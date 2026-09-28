import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import 'activity_timeline_provider.dart';
class ActivityTimelineScreen extends ConsumerWidget {
  const ActivityTimelineScreen({super.key});
  $dialog
  @override Widget build(BuildContext context, WidgetRef ref) {
    final parcels = ref.watch(parcelsProvider);
    final selected = ref.watch(selectedTimelineParcelProvider);
    ref.watch(activityTimelineRefreshProvider);
    return AppPage(title: 'Línea temporal', subtitle: 'Actividad, telemetría y riesgo de la parcela', child: parcels.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('No se pudieron cargar las parcelas: ' + e.toString())),
      data: (items) {
        final current = items.where((p) => p.id == selected).firstOrNull;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          DropdownButton<String>(value: current?.id, hint: const Text('Selecciona una parcela'), items: [for (final p in items) DropdownMenuItem(value: p.id, child: Text(p.name))], onChanged: (v) => ref.read(selectedTimelineParcelProvider.notifier).state = v),
          const SizedBox(height: 12),Row(children: [FilledButton.icon(onPressed: current == null ? null : () => _createActivity(context, ref, current.id), icon: const Icon(Icons.add), label: const Text('Registrar actividad')), const SizedBox(width: 8), OutlinedButton.icon(onPressed: current == null ? null : () => ref.invalidate(activityTimelineProvider), icon: const Icon(Icons.refresh), label: const Text('Actualizar'))]),
          Expanded(child: ref.watch(activityTimelineProvider).when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('No se pudo cargar la línea temporal: ' + e.toString())),
            data: (events) => events.isEmpty ? const Center(child: Text('No hay actividad registrada.')) : ListView.separated(
              itemCount: events.length, separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) { final event = events[i]; return ListTile(leading: Icon(_icon(event['event_type']?.toString() ?? '')), title: Text(event['title']?.toString() ?? 'Evento'), subtitle: Text((event['detail']?.toString() ?? '') + '\n' + (event['occurred_at']?.toString() ?? '')), isThreeLine: true); },
            ),
          )),
        ]);
      },
    ));
  }
  IconData _icon(String type) => switch (type) { 'riesgo' => Icons.warning_amber_rounded, 'telemetria' => Icons.thermostat_outlined, 'actividad' => Icons.task_alt_outlined, _ => Icons.timeline };
}