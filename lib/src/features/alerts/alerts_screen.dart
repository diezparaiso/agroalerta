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
    subtitle: 'Señales calculadas con clima y datos agroclimáticos',
    showAds: false,
    child: ref.watch(alertsProvider).when(
      data: (alerts) => alerts.isEmpty
        ? const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('Todavía no hay avisos calculados para las parcelas disponibles.')))
        : ListView(children: [
        for (final alert in alerts)
          _AlertTile(title: alert.title, parcel: alert.parcel, level: alert.level, value: alert.value, dataStatus: alert.dataStatus,
            color: alert.level.toLowerCase() == 'alto' ? Colors.red : alert.level.toLowerCase() == 'medio' ? Colors.amber : Colors.green),
      ]),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(child: Text('No se pudieron cargar los avisos: $error')),
    ),
  );
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.title, required this.parcel, required this.level, required this.value, required this.color, required this.dataStatus});
  final String title, parcel, level;
  final double value;
  final Color color;
  final String dataStatus;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: ListTile(
      onTap: () => context.push('/alerts/${title.toLowerCase()}?parcelId=${Uri.encodeComponent(parcel)}'),
      contentPadding: const EdgeInsets.all(16),
      leading: CircleAvatar(backgroundColor: color.withValues(alpha: .2), child: Icon(Icons.warning_amber_rounded, color: color)),
      title: Text('$title · riesgo $level', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Padding(padding: const EdgeInsets.only(top: 8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(parcel), const SizedBox(height: 6), Text(dataStatus == 'preliminar' ? 'Indicador preliminar · no validado' : 'Datos insuficientes para estimar el riesgo', style: Theme.of(context).textTheme.bodySmall), const SizedBox(height: 10), LinearProgressIndicator(value: value, color: color)])),
      trailing: const Icon(Icons.chevron_right),
    ),
  );
}
