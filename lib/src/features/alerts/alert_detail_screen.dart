import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import 'risk_history_chart.dart';
import 'risk_history_provider.dart';

final parcelRiskProvider = FutureProvider.family<List<Map<String, dynamic>>, String>(
  (ref, parcelId) => ref.read(apiClientProvider).getRisk(parcelId),
);

class AlertDetailScreen extends ConsumerWidget {
  const AlertDetailScreen({required this.disease, this.parcelId, super.key});
  final String disease;
  final String? parcelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPage(
    title: 'Detalle de $disease',
    subtitle: parcelId == null ? 'Información del indicador de riesgo' : 'Parcela: $parcelId',
    showAds: false,
    child: ListView(children: [
      if (parcelId == null)
        const _InfoCard(message: 'No se ha identificado la parcela. Vuelve a la lista de avisos y selecciona una parcela para consultar los datos reales.')
      else
        ref.watch(parcelRiskProvider(parcelId!)).when(
          loading: () => const Card(child: Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()))),
          error: (_, __) => const _InfoCard(message: 'No se pudo cargar el riesgo de esta parcela. Comprueba la conexión y vuelve a intentarlo.'),
          data: (records) {
            final code = disease.toLowerCase();
            final matches = records.where((item) => (item['disease_code'] as String? ?? '').toLowerCase() == code).toList();
            if (matches.isEmpty) {
              return const _InfoCard(message: 'La API no ha devuelto un cálculo para esta enfermedad en la parcela seleccionada.');
            }
            final risk = matches.last;
            final score = ((risk['risk_score'] as num?)?.toDouble() ?? 0).clamp(0.0, 1.0).toDouble();
            final level = risk['risk_level'] as String? ?? 'desconocido';
            final status = risk['data_status'] as String? ?? 'insuficiente';
            final variables = (risk['variables_used'] as List<dynamic>? ?? const []);
            final recommendation = risk['recommendation_text'] as String? ?? 'No hay explicación disponible.';
            final color = level == 'alto' ? Colors.red : level == 'medio' ? Colors.amber.shade800 : Colors.green;
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [Icon(Icons.analytics_outlined, color: color, size: 30), const SizedBox(width: 12), Expanded(child: Text('Riesgo $level', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)))]),
                const SizedBox(height: 18),
                LinearProgressIndicator(value: score, color: color),
                const SizedBox(height: 10),
                Text('Índice: ${(score * 100).round()} %'),
                const SizedBox(height: 8),
                Text(status == 'preliminar' ? 'Indicador preliminar · no validado' : 'Datos insuficientes para estimar el riesgo'),
                if (risk['calculated_at'] != null) ...[
                  const SizedBox(height: 8),
                  Text('Calculado: ${risk['calculated_at']}', style: Theme.of(context).textTheme.bodySmall),
                ],
              ]))),
              const SizedBox(height: 16),
              Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Variables utilizadas', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 12),
                if (variables.isEmpty)
                  const Text('No hay variables disponibles para este cálculo.')
                else
                  for (final item in variables)
                    if (item is Map<String, dynamic>)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.sensors_outlined),
                        title: Text((item['name'] as String? ?? 'Variable').replaceAll('_', ' ')),
                        trailing: Text(item['value']?.toString() ?? '—'),
                        subtitle: item['date'] == null ? null : Text(item['date'].toString()),
                      ),
              ]))),
              const SizedBox(height: 16),
              Card(color: Theme.of(context).colorScheme.secondaryContainer, child: Padding(padding: const EdgeInsets.all(20), child: Text(recommendation))),
            ]);
          },
        ),
      const SizedBox(height: 16),
      Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Evolución del riesgo', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        parcelId == null ? const _InfoCard(message: 'Selecciona una parcela para consultar el histórico.') : ref.watch(riskHistoryProvider(parcelId!)).when(
          data: (history) => history.isEmpty ? const Text('Todavía no hay datos históricos.') : RiskHistoryChart(spots: [for (var i = 0; i < history.length; i++) FlSpot(i.toDouble(), history[i].score)]),
          loading: () => const SizedBox(height: 190, child: Center(child: CircularProgressIndicator())),
          error: (_, __) => const Text('No se pudo cargar el histórico de riesgo.'),
        ),
      ]))),
      const SizedBox(height: 16),
      Text('Aviso legal', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      const Text('Los indicadores son orientativos y no constituyen un diagnóstico. No realices tratamientos basándote únicamente en este resultado. Consulta a un técnico agrícola y verifica la autorización vigente en el registro oficial del MAPA.'),
    ]),
  );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(20), child: Text(message)));
}
