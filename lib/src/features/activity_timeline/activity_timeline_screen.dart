import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import 'activity_timeline_provider.dart';

class ActivityTimelineScreen extends ConsumerWidget {
  const ActivityTimelineScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final parcels = ref.watch(parcelsProvider);
    final selected = ref.watch(selectedTimelineParcelProvider);
    return AppPage(title: 'Línea temporal', subtitle: 'Actividad, telemetría y riesgo de la parcela', child: parcels.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('No se pudieron cargar las parcelas: $e')),
      data: (items) {
        final current = items.where((p) => p.id == selected).firstOrNull;
            final currentId = current?.id;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          DropdownButton<String>(
            value: currentId,
            hint: const Text('Selecciona una parcela'),
            items: [for (final p in items) DropdownMenuItem(value: p.id, child: Text(p.name))],
            onChanged: (v) => ref.read(selectedTimelineParcelProvider.notifier).state = v,
          ),
          const SizedBox(height: 12),
          Row(children: [
            FilledButton.icon(
              onPressed: currentId == null ? null : () => _createActivity(context, ref, currentId),
              icon: const Icon(Icons.add), label: const Text('Registrar actividad'),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: currentId == null ? null : () => ref.invalidate(activityTimelineProvider),
              icon: const Icon(Icons.refresh), label: const Text('Actualizar'),
            ),
          ]),
          const SizedBox(height: 12),
          Expanded(child: ref.watch(activityTimelineProvider).when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('No se pudo cargar la línea temporal: $e')),
            data: (events) => events.isEmpty ? const Center(child: Text('No hay actividad registrada.')) : ListView.separated(
              itemCount: events.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final event = events[i];
                return ListTile(
                  leading: Icon(_icon(event['event_type']?.toString() ?? '')),
                  title: Text(event['title']?.toString() ?? 'Evento'),
                  subtitle: Text('${event['detail']?.toString() ?? ''}\n${event['occurred_at']?.toString() ?? ''}'),
                  isThreeLine: true,
                );
              },
            ),
          )),
        ]);
      },
    ));
  }
  IconData _icon(String type) => switch (type) {
    'riesgo' => Icons.warning_amber_rounded,
    'telemetria' => Icons.thermostat_outlined,
    'actividad' => Icons.task_alt_outlined,
    _ => Icons.timeline
  };
}

Future<void> _createActivity(BuildContext context, WidgetRef ref, String parcelId) async {
  final title = TextEditingController();
  final detail = TextEditingController();
  final quantity = TextEditingController();
  final unit = TextEditingController();
  var activityType = 'labor';

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('Registrar actividad'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButtonFormField<String>(
            initialValue: activityType,
            decoration: const InputDecoration(labelText: 'Tipo'),
            items: const [
              DropdownMenuItem(value: 'labor', child: Text('Trabajo')),
              DropdownMenuItem(value: 'irrigation', child: Text('Riego')),
              DropdownMenuItem(value: 'treatment', child: Text('Tratamiento')),
              DropdownMenuItem(value: 'observation', child: Text('Observación')),
              DropdownMenuItem(value: 'harvest', child: Text('Cosecha')),
            ],
            onChanged: (value) => setState(() => activityType = value ?? 'labor'),
          ),
          TextField(controller: title, decoration: const InputDecoration(labelText: 'Título')),
          TextField(controller: detail, decoration: const InputDecoration(labelText: 'Detalle')),
          TextField(controller: quantity, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Cantidad (opcional)')),
          TextField(controller: unit, decoration: const InputDecoration(labelText: 'Unidad (opcional)')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () async {
              if (title.text.trim().isEmpty) return;
              await ref.read(apiClientProvider).createActivity(
                parcelId: parcelId,
                activityType: activityType,
                title: title.text.trim(),
                detail: detail.text.trim().isEmpty ? null : detail.text.trim(),
                occurredAt: DateTime.now(),
                quantity: double.tryParse(quantity.text.replaceAll(',', '.')),
                unit: unit.text.trim().isEmpty ? null : unit.text.trim(),
              );
              ref.invalidate(activityTimelineProvider);
              if (dialogContext.mounted) Navigator.pop(dialogContext);
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    ),
  );
}
