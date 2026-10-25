import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/error_view.dart';
import '../home/home_screen.dart';
import 'operation_center_provider.dart';

class OperationCenterScreen extends ConsumerWidget {
  const OperationCenterScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppPage(
      title: 'Centro de explotación',
      subtitle: 'Estado operativo de tus parcelas',
      child: ref.watch(operationCenterProvider).when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => ErrorView(message: 'No se pudo cargar el centro de explotación.', onRetry: () => ref.invalidate(operationCenterProvider)),
        data: (center) => _CenterContent(center: center),
      ),
    );
  }
}

class _CenterContent extends StatelessWidget {
  const _CenterContent({required this.center});
  final Map<String, dynamic> center;

  @override
  Widget build(BuildContext context) {
    final parcels = (center['parcels'] as List<dynamic>? ?? const []).cast<Map<String, dynamic>>();
    final events = (center['recent_events'] as List<dynamic>? ?? const []).cast<Map<String, dynamic>>();

    return ListView(
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _Metric(label: 'Parcelas', value: '${center['parcel_count'] ?? 0}'),
            _Metric(label: 'En atención', value: '${center['parcel_attention_count'] ?? 0}'),
            _Metric(label: 'Sensores', value: '${center['sensor_count'] ?? 0}'),
          ],
        ),
        const SizedBox(height: 20),
        Text('Parcelas', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 10),
        ...parcels.map((parcel) => Card(
          child: ListTile(
            leading: const Icon(Icons.landscape_outlined),
            title: Text('${parcel['label'] ?? 'Parcela'}'),
            subtitle: Text('${parcel['crop_type'] ?? ''} · ${parcel['comarca'] ?? ''}'),
            trailing: _PriorityChip(priority: '${parcel['priority'] ?? 'normal'}'),
          ),
        )),
        const SizedBox(height: 20),
        Text('Actividad reciente', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 10),
        if (events.isEmpty)
          const Card(child: ListTile(title: Text('Sin eventos recientes.')))
        else
          ...events.map((event) => Card(
            child: ListTile(
              leading: Icon(_eventIcon('${event['event_type']}')),
              title: Text('${event['title'] ?? 'Evento'}'),
              subtitle: Text('${event['detail'] ?? ''}\n${event['occurred_at'] ?? ''}'),
              isThreeLine: true,
            ),
          )),
      ],
    );
  }

  IconData _eventIcon(String type) => switch (type) {
    'riesgo' => Icons.warning_amber_rounded,
    'telemetria' => Icons.thermostat_outlined,
    _ => Icons.sensors_outlined,
  };
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 180,
    child: Card(child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(value, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700)),
        Text(label),
      ]),
    )),
  );
}

class _PriorityChip extends StatelessWidget {
  const _PriorityChip({required this.priority});
  final String priority;

  @override
  Widget build(BuildContext context) => Chip(label: Text(priority));
}
