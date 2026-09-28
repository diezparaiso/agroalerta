import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../home/home_screen.dart';
import 'alerts_provider.dart';
import 'risk_history_chart.dart';
import 'risk_history_provider.dart';

class AlertDetailScreen extends ConsumerWidget {
  const AlertDetailScreen({required this.disease, this.parcelId, super.key});

  final String disease;
  final String? parcelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerts = ref.watch(alertsProvider);

    return AppPage(
      title: 'Detalle de $disease',
      subtitle: parcelId == null ? 'Sin parcela seleccionada' : 'Parcela $parcelId',
      showAds: false,
      child: alerts.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('No se pudo cargar el aviso: $error')),
        data: (records) {
          final matching = records.where(
            (alert) =>
                alert.title.toLowerCase() == disease.toLowerCase() &&
                (parcelId == null || alert.parcel == parcelId),
          );
          final alert = matching.isEmpty ? null : matching.first;

          return ListView(
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.warning_amber_rounded, color: Colors.amber.shade800, size: 32),
                          const SizedBox(width: 12),
                          Text(
                            alert == null ? 'Riesgo no disponible' : 'Riesgo ${alert.level.toLowerCase()}',
                            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
                          ),
                        ],
                      ),
                      const SizedBox(height: 18),
                      LinearProgressIndicator(value: alert?.value),
                      const SizedBox(height: 12),
                      Text(
                        alert == null
                            ? 'No existe un aviso persistido para esta combinación de enfermedad y parcela.'
                            : 'Nivel calculado a partir de las evidencias disponibles en el backend.',
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text('Variables utilizadas', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                      SizedBox(height: 16),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.water_drop_outlined),
                        title: Text('Lluvia acumulada'),
                        trailing: Text('No disponible'),
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.thermostat_outlined),
                        title: Text('Temperatura media'),
                        trailing: Text('No disponible'),
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.opacity_outlined),
                        title: Text('Humedad'),
                        trailing: Text('No disponible'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Evolución del riesgo', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 12),
                      parcelId == null
                          ? const RiskHistoryChart()
                          : ref.watch(riskHistoryProvider(parcelId!)).when(
                              data: (history) => RiskHistoryChart(
                                spots: [
                                  for (var index = 0; index < history.length; index++)
                                    FlSpot(index.toDouble(), history[index].score),
                                ],
                              ),
                              loading: () => const SizedBox(
                                height: 190,
                                child: Center(child: CircularProgressIndicator()),
                              ),
                              error: (_, __) => const RiskHistoryChart(),
                            ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                color: Theme.of(context).colorScheme.secondaryContainer,
                child: const Padding(
                  padding: EdgeInsets.all(20),
                  child: Text(
                    'Recomendación orientativa: revisa la parcela y consulta la etiqueta del producto autorizado antes de realizar cualquier tratamiento.',
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text('Aviso legal', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              const Text(
                'Este aviso no constituye un diagnóstico ni sustituye el asesoramiento de un técnico agrícola cualificado. La autorización, dosis y plazo de seguridad deben comprobarse en el registro oficial del MAPA vigente.',
              ),
            ],
          );
        },
      ),
    );
  }
}
