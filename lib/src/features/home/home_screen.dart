import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ads/ad_banner.dart';
import '../alerts/alerts_provider.dart';
import '../parcels/parcel_map_preview.dart';
import '../parcels/parcel_provider.dart';
import 'telemetry_provider.dart';
import 'weather_provider.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppPage(
      title: 'AgroAlerta',
      subtitle: 'Tu panel agrícola',
      actions: [
        IconButton(
          tooltip: 'Avisos',
          onPressed: () => context.go('/alerts'),
          icon: const Icon(Icons.notifications_none_rounded),
        ),
      ],
      child: LayoutBuilder(
        builder: (context, constraints) {
          final columns = constraints.maxWidth >= 1100
              ? 3
              : constraints.maxWidth >= 700
                  ? 2
                  : 1;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _WelcomeBanner(),
                const SizedBox(height: 16),
                _SummaryGrid(columns: columns),
                const SizedBox(height: 16),
                if (columns == 1)
                  const Column(
                    children: [
                      _MapCard(),
                      SizedBox(height: 16),
                      _AlertsCard(),
                      SizedBox(height: 16),
                      _TelemetryCard(),
                    ],
                  )
                else
                  const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 3, child: _MapCard()),
                      SizedBox(width: 16),
                      Expanded(flex: 2, child: _AlertsCard()),
                    ],
                  ),
                if (columns >= 2) ...[
                  const SizedBox(height: 16),
                  const _TelemetryCard(),
                ],
                const SizedBox(height: 12),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _WelcomeBanner extends StatelessWidget {
  const _WelcomeBanner();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [scheme.primary, scheme.primaryContainer],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 22, 24, 22),
        child: Row(
          children: [
            CircleAvatar(
              radius: 26,
              backgroundColor: scheme.onPrimary.withValues(alpha: 0.16),
              child: Icon(Icons.eco_rounded, color: scheme.onPrimary, size: 30),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                'Estado de tus cultivos y avisos fitosanitarios en un solo lugar.',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: scheme.onPrimary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
            ),
            if (MediaQuery.sizeOf(context).width >= 700)
              FilledButton.tonal(
                onPressed: () => context.go('/parcels'),
                child: const Text('Ver parcelas'),
              ),
          ],
        ),
      ),
    );
  }
}

class _SummaryGrid extends StatelessWidget {
  const _SummaryGrid({required this.columns});

  final int columns;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = (constraints.maxWidth - ((columns - 1) * 16)) / columns;
        return Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(width: width, child: const _WeatherCard()),
            SizedBox(width: width, child: const _RiskCard()),
            SizedBox(width: width, child: const _ParcelSummaryCard()),
          ],
        );
      },
    );
  }
}

class _WeatherCard extends ConsumerWidget {
  const _WeatherCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Panel(
      title: 'Meteorología',
      icon: Icons.cloud_outlined,
      child: ref.watch(weatherProvider).when(
        data: (weather) {
          final temperature = weatherDisplayValue(weather, 'temperature_c');
          final humidity = weatherDisplayValue(weather, 'relative_humidity');
          final rain = weatherDisplayValue(weather, 'rainfall_mm_24h');
          final source = weatherDisplayValue(weather, 'source');

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                temperature == 'No disponible' ? temperature : '$temperature °C',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 8),
              Text('Humedad: $humidity %'),
              Text('Lluvia 24 h: $rain mm'),
              const SizedBox(height: 18),
              Text(
                source == 'none' ? 'Datos meteorológicos no disponibles' : 'Fuente: $source',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Text('Meteorología no disponible'),
      ),
    );
  }
}

class _RiskCard extends ConsumerWidget {
  const _RiskCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Panel(
      title: 'Avisos activos',
      icon: Icons.warning_amber_rounded,
      child: ref.watch(alertsProvider).when(
        data: (alerts) {
          final highRisk = alerts.where(
            (alert) => alert.level.toLowerCase() == 'high' || alert.level.toLowerCase() == 'alto',
          ).length;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${alerts.length}',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              Text(alerts.length == 1 ? 'aviso requiere atención' : 'avisos registrados'),
              const SizedBox(height: 18),
              if (highRisk > 0)
                Text(
                  '$highRisk de nivel alto',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                )
              else
                const Text('Sin avisos de nivel alto'),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Text('Avisos no disponibles'),
      ),
    );
  }
}

class _ParcelSummaryCard extends ConsumerWidget {
  const _ParcelSummaryCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Panel(
      title: 'Tus parcelas',
      icon: Icons.agriculture_outlined,
      child: ref.watch(parcelsProvider).when(
        data: (parcels) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${parcels.length}',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const Text('parcelas disponibles'),
            const SizedBox(height: 18),
            Text(
              parcels.isEmpty ? 'Añade tu primera parcela' : 'Datos sincronizados',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Text('Parcelas no disponibles'),
      ),
    );
  }
}

class _MapCard extends StatelessWidget {
  const _MapCard();

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'Tus parcelas',
      icon: Icons.map_outlined,
      action: TextButton(
        onPressed: () => context.go('/parcels'),
        child: const Text('Ver todas'),
      ),
      child: const SizedBox(height: 300, child: ParcelMapPreview()),
    );
  }
}

class _AlertsCard extends ConsumerWidget {
  const _AlertsCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Panel(
      title: 'Alertas recientes',
      icon: Icons.notifications_active_outlined,
      action: TextButton(
        onPressed: () => context.go('/alerts'),
        child: const Text('Ver todas'),
      ),
      child: ref.watch(alertsProvider).when(
        data: (alerts) {
          if (alerts.isEmpty) {
            return const Center(child: Text('No hay alertas persistidas.'));
          }

          return ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: alerts.length > 3 ? 3 : alerts.length,
            separatorBuilder: (_, __) => const Divider(height: 18),
            itemBuilder: (context, index) {
              final alert = alerts[index];
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.errorContainer,
                  child: Icon(
                    Icons.priority_high_rounded,
                    color: Theme.of(context).colorScheme.onErrorContainer,
                  ),
                ),
                title: Text(alert.title),
                subtitle: Text('${alert.parcel} · ${alert.level}'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => context.go('/alerts/${alert.title}?parcelId=${alert.parcel}'),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Text('Alertas no disponibles'),
      ),
    );
  }
}

class _TelemetryCard extends ConsumerWidget {
  const _TelemetryCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final window = ref.watch(telemetryWindowProvider);
    return _Panel(
      title: 'Sensores',
      icon: Icons.sensors_outlined,
      action: SegmentedButton<TelemetryWindow>(
        segments: const [
          ButtonSegment(value: TelemetryWindow(24), label: Text('24 h')),
          ButtonSegment(value: TelemetryWindow(168), label: Text('7 días')),
        ],
        selected: {window},
        onSelectionChanged: (selection) {
          ref.read(telemetryWindowProvider.notifier).state = selection.first;
        },
      ),
      child: ref.watch(telemetryHistoryProvider).when(
        data: (history) {
          if (history.isEmpty) {
            return const Text('No hay mediciones reales en el periodo seleccionado.');
          }
          final temperature = telemetrySeries(history, 'temperature_c');
          if (temperature.isEmpty) {
            return const Text('No hay temperatura disponible en el periodo seleccionado.');
          }
          final values = temperature.map((item) => (item['temperature_c'] as num).toDouble()).toList();
          final min = values.reduce((a, b) => a < b ? a : b);
          final max = values.reduce((a, b) => a > b ? a : b);
          final range = max - min;
          final padding = range == 0 ? 1.0 : range * 0.15;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Temperatura · ${window.label}', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              SizedBox(
                height: 190,
                child: LineChart(
                  LineChartData(
                    minY: min - padding,
                    maxY: max + padding,
                    gridData: const FlGridData(show: true),
                    titlesData: const FlTitlesData(show: false),
                    borderData: FlBorderData(show: false),
                    lineBarsData: [
                      LineChartBarData(
                        spots: [
                          for (var i = 0; i < values.length; i++) FlSpot(i.toDouble(), values[i]),
                        ],
                        isCurved: false,
                        dotData: const FlDotData(show: false),
                        barWidth: 2,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 24,
                runSpacing: 8,
                children: [
                  _Metric(label: 'Actual', value: '${values.last} °C'),
                  _Metric(label: 'Mínima', value: '$min °C'),
                  _Metric(label: 'Máxima', value: '$max °C'),
                  _Metric(label: 'Mediciones', value: '${values.length}'),
                ],
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Text('Telemetría no disponible'),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 4),
        Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      ],
    );
  }
}

class AppPage extends StatelessWidget {
  const AppPage({
    required this.title,
    required this.child,
    this.subtitle,
    this.actions,
    this.showAds = true,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final List<Widget>? actions;
  final bool showAds;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    if (subtitle != null)
                      Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              if (actions != null) ...actions!,
            ],
          ),
          const SizedBox(height: 18),
          Expanded(child: child),
          if (showAds)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Center(child: AdBanner()),
            ),
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    required this.title,
    required this.icon,
    required this.child,
    this.action,
  });

  final String title;
  final IconData icon;
  final Widget child;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                  ),
                ),
                if (action != null) action!,
              ],
            ),
            const SizedBox(height: 18),
            child,
          ],
        ),
      ),
    );
  }
}
