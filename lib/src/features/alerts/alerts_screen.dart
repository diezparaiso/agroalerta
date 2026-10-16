import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../home/home_screen.dart';
import 'alerts_provider.dart';

class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPage(
        title: 'Avisos de riesgo',
        subtitle: 'Señales calculadas con clima y datos agroclimaticos',
        showAds: false,
        child: ref.watch(alertsProvider).when(
          data: (alerts) => alerts.isEmpty
              ? const Center(child: Text('No hay avisos activos para tus parcelas.'))
              : ListView(children: [for (final alert in alerts) _AlertTile(alert: alert)]),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, stack) => Center(child: Text('No se pudieron cargar los avisos: $error')),
        ),
      );
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert});
  final AlertSummary alert;
  @override
  Widget build(BuildContext context) {
    final normalized = alert.level.toLowerCase();
    final color = normalized == 'alto' ? Colors.red : normalized == 'medio' ? Colors.amber : Colors.green;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        onTap: alert.parcelId == null ? null : () => context.push('/alerts/' + alert.title.toLowerCase() + '?parcelId=' + Uri.encodeComponent(alert.parcelId!)),
        contentPadding: const EdgeInsets.all(16),
        leading: CircleAvatar(backgroundColor: color.withValues(alpha: .2), child: Icon(Icons.warning_amber_rounded, color: color)),
        title: Text(alert.title + ' · riesgo ' + alert.level, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Padding(padding: const EdgeInsets.only(top: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(alert.parcel), const SizedBox(height: 10), LinearProgressIndicator(value: alert.value, color: color)])),
        trailing: alert.parcelId == null ? null : const Icon(Icons.chevron_right),
      ),
    );
  }
}
