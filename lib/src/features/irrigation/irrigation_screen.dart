import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/ui/error_view.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';

class IrrigationScreen extends ConsumerStatefulWidget {
  const IrrigationScreen({super.key});
  @override ConsumerState<IrrigationScreen> createState() => _IrrigationScreenState();
}
class _IrrigationScreenState extends ConsumerState<IrrigationScreen> {
  String? parcelId;
  Map<String, dynamic>? data;
  Object? error;
  bool loading = false;

  Future<void> load() async {
    if (parcelId == null) return;
    setState(() { loading = true; error = null; });
    try {
      final value = await ref.read(apiClientProvider).getIrrigationIntelligence(parcelId!);
      if (mounted) setState(() => data = value);
    } catch (e) {
      if (mounted) setState(() { error = e; data = null; });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final parcels = ref.watch(parcelsProvider);
    return AppPage(
      title: 'Inteligencia hídrica',
      subtitle: 'Histórico de riego y estado de humedad',
      child: parcels.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(message: 'No se pudieron cargar las parcelas.', onRetry: () => ref.invalidate(parcelsProvider)),
        data: (items) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Expanded(
                child: DropdownButton<String>(
                  value: parcelId,
                  isExpanded: true,
                  hint: const Text('Parcela'),
                  items: [for (final p in items) DropdownMenuItem(value: p.id, child: Text(p.name))],
                  onChanged: (v) => setState(() => parcelId = v),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton(onPressed: loading ? null : load, child: const Text('Consultar')),
            ]),
            if (loading) const LinearProgressIndicator(),
            if (error != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('No se pudo consultar la inteligencia hídrica.', style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(onPressed: load, icon: const Icon(Icons.refresh), label: const Text('Reintentar')),
                ]),
              ),
            if (data != null)
              Expanded(
                child: ListView(children: [
                  Card(child: ListTile(
                    title: Text('Estado: ${data!['soil_status']?.toString() ?? ''}'),
                    subtitle: Text('${data!['explanation']?.toString() ?? ''}\nAcción: ${data!['action']?.toString() ?? ''}'),
                  )),
                  Card(child: ListTile(
                    title: Text('Agua registrada: ${data!['total_water_liters']?.toString() ?? '0'} L'),
                    subtitle: Text('Eventos: ${data!['event_count']?.toString() ?? '0'} · Nivel de uso: ${data!['water_use_level']?.toString() ?? ''}'),
                  )),
                  Text('Evidencias', style: Theme.of(context).textTheme.titleLarge),
                  ...((data!['evidence'] as List<dynamic>? ?? const []).map((e) => ListTile(
                    leading: const Icon(Icons.water_drop_outlined), title: Text(e.toString()),
                  ))),
                ]),
              ),
          ],
        ),
      ),
    );
  }
}
