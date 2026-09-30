import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../core/network/api_client.dart';
import '../home/home_screen.dart';
import 'risk_history_chart.dart';
import 'risk_history_provider.dart';
import '../parcels/parcel_provider.dart';

final alertRiskProvider = FutureProvider.family<Map<String, dynamic>?, ({String parcelId, String disease})>((ref, key) async {
  final risks = await ref.read(apiClientProvider).getRisk(key.parcelId);
  for (final risk in risks) {
    if ((risk['disease_code'] as String?)?.toLowerCase() == key.disease.toLowerCase()) return risk;
  }
  return risks.isEmpty ? null : risks.first;
});

class AlertDetailScreen extends ConsumerWidget {
  const AlertDetailScreen({required this.disease, this.parcelId, super.key});
  final String disease;
  final String? parcelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final riskAsync = parcelId == null ? null : ref.watch(alertRiskProvider((parcelId: parcelId!, disease: disease)));
    final risk = riskAsync?.valueOrNull;
    final score = (risk?['risk_score'] as num?)?.toDouble() ?? .58;
    final level = (risk?['risk_level'] as String? ?? 'medio').toLowerCase();
    final confidence = risk?['confidence_level'] as String? ?? 'estimada';
    final recommendation = risk?['recommendation_text'] as String? ?? 'Revisa la parcela y consulta la etiqueta del producto autorizado antes de realizar cualquier tratamiento.';

    return AppPage(
      title: 'Detalle de ' + disease,
      subtitle: parcelId == null ? 'Olivar de prueba' : 'Riesgo de parcela monitorizada',
      showAds: false,
      child: ListView(children: [
        Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Icon(Icons.warning_amber_rounded, color: Colors.amber.shade800, size: 32), const SizedBox(width: 12), Text('Riesgo ' + level, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700))]),
          const SizedBox(height: 18),
          LinearProgressIndicator(value: score),
          const SizedBox(height: 12),
          Text('Confianza $confidence · puntuacion ${(score * 100).round()}%.'),
        ]))),
        const SizedBox(height: 16),
        Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Variables utilizadas', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 16),
          if (risk?['variables_used'] is List && (risk!['variables_used'] as List).isNotEmpty)
            for (final variable in (risk['variables_used'] as List))
              ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.analytics_outlined), title: Text((variable['name'] ?? 'Variable').toString()), trailing: Text((variable['value'] ?? '--').toString())),
          if (risk == null) ...const [
            ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.water_drop_outlined), title: Text('Lluvia acumulada'), trailing: Text('12,2 mm')),
            ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.thermostat_outlined), title: Text('Temperatura media'), trailing: Text('18,4 °C')),
          ],
        ]))),
        const SizedBox(height: 16),
        Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Evolución del riesgo', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          parcelId == null ? const RiskHistoryChart() : ref.watch(riskHistoryProvider(parcelId!)).when(
            data: (history) => history.isEmpty ? const Text('Aún no hay historial suficiente.') : RiskHistoryChart(spots: [for (var index = 0; index < history.length; index++) FlSpot(index.toDouble(), history[index].score)]),
            loading: () => const SizedBox(height: 190, child: Center(child: CircularProgressIndicator())),
            error: (_, __) => const RiskHistoryChart(),
          ),
        ]))),
        const SizedBox(height: 16),
        Card(color: Theme.of(context).colorScheme.secondaryContainer, child: Padding(padding: const EdgeInsets.all(20), child: Text(recommendation))),
        const SizedBox(height: 16),
        Text('Aviso legal', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        const Text('Este aviso no constituye un diagnóstico ni sustituye el asesoramiento de un técnico agrícola cualificado. La autorización, dosis y plazo de seguridad deben comprobarse en el registro oficial del MAPA vigente.'),
      ]),
    );
  }
}
