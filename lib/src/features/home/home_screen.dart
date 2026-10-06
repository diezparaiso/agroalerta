import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ads/ad_banner.dart';
import '../alerts/alerts_provider.dart';
import '../parcels/parcel_map_preview.dart';
import '../parcels/parcel_provider.dart';
import 'telemetry_provider.dart';
import 'weather_provider.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});
  @override
  Widget build(BuildContext context) => AppPage(
    title: 'Buenos dias, agricultor',
    subtitle: 'Andalucia · monitorizacion de tus parcelas',
    actions: [IconButton(onPressed: () {}, icon: const Icon(Icons.notifications_none))],
    child: LayoutBuilder(builder: (context, constraints) {
      final columns = constraints.maxWidth >= 1100 ? 3 : constraints.maxWidth >= 650 ? 2 : 1;
      return GridView.count(
        crossAxisCount: columns,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: columns == 1 ? 2.1 : 1.45,
        children: const [_WeatherCard(), _RiskCard(), _ParcelSummaryCard(), _InsightCard(), _MapCard(), _TelemetryCard()],
      );
    }),
  );
}

class _WeatherCard extends ConsumerWidget {
  const _WeatherCard();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _Panel(
    title: 'Condiciones de hoy',
    icon: Icons.wb_sunny_outlined,
    child: ref.watch(weatherProvider).when(
      data: (weather) => Row(children: [
        Text('${weather['temperature_c'] ?? '--'}°', style: const TextStyle(fontSize: 42, fontWeight: FontWeight.w700)),
        const SizedBox(width: 18),
        Text('Humedad ${weather['relative_humidity'] ?? '--'}%\nLluvia ${weather['rainfall_mm_24h'] ?? '--'} mm\nFuente: ${weather['source'] ?? 'estimada'}${weather['cached'] == true ? ' · datos en caché' : ''}', style: const TextStyle(height: 1.6)),
      ]),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => Row(children: [const Text('Clima no disponible'), TextButton(onPressed: () => ref.invalidate(weatherProvider), child: const Text('Reintentar'))]),
    ),
  );
}

class _RiskCard extends ConsumerWidget {
  const _RiskCard();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _Panel(
    title: 'Aviso prioritario',
    icon: Icons.warning_amber_rounded,
    color: Colors.amber.shade100,
    child: ref.watch(alertsProvider).when(
      data: (alerts) {
        if (alerts.isEmpty) return const Text('Sin avisos activos.');
        final alert = alerts.first;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${alert.title} · riesgo ${alert.level}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          LinearProgressIndicator(value: alert.value),
          const SizedBox(height: 10),
          Text(alert.parcel),
        ]);
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => Row(children: [const Text('Avisos no disponibles'), TextButton(onPressed: () => ref.invalidate(alertsProvider), child: const Text('Reintentar'))]),
    ),
  );
}

class _ParcelSummaryCard extends ConsumerWidget {
  const _ParcelSummaryCard();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _Panel(
    title: 'Tus parcelas',
    icon: Icons.landscape_outlined,
    child: ref.watch(parcelsProvider).when(
      data: (parcels) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${parcels.length}', style: const TextStyle(fontSize: 42, fontWeight: FontWeight.w700)),
        const Text('parcelas monitorizadas'),
        const Spacer(),
        Text('${parcels.where((parcel) => parcel.risk.toLowerCase() != 'bajo').length} con seguimiento de riesgo'),
      ]),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => Row(children: [const Text('Parcelas no disponibles'), TextButton(onPressed: () => ref.invalidate(parcelsProvider), child: const Text('Reintentar'))]),
    ),
  );
}

class _InsightCard extends StatelessWidget {
  const _InsightCard();
  @override
  Widget build(BuildContext context) => const _Panel(title: 'Recomendacion', icon: Icons.lightbulb_outline, child: Text('Revisa las hojas bajas del olivar tras los episodios de lluvia. Las alertas son orientativas y deben contrastarse con un técnico.'));
}

class _MapCard extends StatelessWidget {
  const _MapCard();
  @override
  Widget build(BuildContext context) => const _Panel(title: 'Mapa de parcelas', icon: Icons.map_outlined, child: ParcelMapPreview());
}

class _TelemetryCard extends ConsumerWidget {
  const _TelemetryCard();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _Panel(
    title: 'Estado del sensor',
    icon: Icons.sensors_outlined,
    child: ref.watch(telemetryProvider).when(
      data: (telemetry) {
        if (telemetry == null) return const Text('Sin sensores conectados\nLos datos se estimarán con la estación agroclimática más cercana.');
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${telemetry['temperature_c'] ?? '--'} °C', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text('Humedad ${telemetry['relative_humidity'] ?? '--'}%'),
          Text('Mojado foliar ${telemetry['leaf_wetness_hours'] ?? '--'} h'),
          const Spacer(),
          Row(children: [const Icon(Icons.battery_5_bar, size: 18), const SizedBox(width: 6), Text('${telemetry['battery_percent'] ?? '--'}% de batería')]),
        ]);
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => Row(children: [const Text('Telemetría no disponible'), TextButton(onPressed: () => ref.invalidate(telemetryProvider), child: const Text('Reintentar'))]),
    ),
  );
}

class AppPage extends StatelessWidget {
  const AppPage({required this.title, required this.child, this.subtitle, this.actions, this.showAds = true, super.key});
  final String title;
  final String? subtitle;
  final Widget child;
  final List<Widget>? actions;
  final bool showAds;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)), if (subtitle != null) Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium)])), ...?actions]),
      const SizedBox(height: 24),
      Expanded(child: child),
      if (showAds) const Padding(padding: EdgeInsets.only(top: 12), child: Center(child: AdBanner())),
    ]),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.icon, required this.child, this.color});
  final String title;
  final IconData icon;
  final Widget child;
  final Color? color;
  @override
  Widget build(BuildContext context) => Card(color: color, child: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Icon(icon), const SizedBox(width: 10), Text(title, style: const TextStyle(fontWeight: FontWeight.w700))]), const SizedBox(height: 18), Expanded(child: child)])));
}
