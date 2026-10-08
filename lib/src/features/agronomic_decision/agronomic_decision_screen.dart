import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/ui/error_view.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';

class AgronomicDecisionScreen extends ConsumerStatefulWidget {
  const AgronomicDecisionScreen({super.key});
  @override ConsumerState<AgronomicDecisionScreen> createState() => _State();
}
class _State extends ConsumerState<AgronomicDecisionScreen> {
  String? parcelId;
  String? diseaseCode;
  Map<String, dynamic>? decision;
  Object? error;
  bool loading = false;

  Future<void> load() async {
    if (parcelId == null || diseaseCode == null) return;
    setState(() { loading = true; error = null; });
    try {
      final values = await ref.read(apiClientProvider).getDecisions(parcelId!, diseaseCode!);
      if (mounted && values.isNotEmpty) setState(() => decision = values.single);
    } catch (e) {
      if (mounted) setState(() => error = e);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final parcels = ref.watch(parcelsProvider);
    return AppPage(
      title: 'Decisión agronómica',
      subtitle: 'Interpretación explicable de las señales disponibles',
      child: parcels.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(message: 'No se pudieron cargar las parcelas.', onRetry: () => ref.invalidate(parcelsProvider)),
        data: (items) => Column(
          children: [
            Wrap(
              spacing: 12,
              children: [
                DropdownButton<String>(
                  value: parcelId,
                  isExpanded: true,
                  hint: const Text('Parcela'),
                  items: [for (final p in items) DropdownMenuItem(value: p.id, child: Text(p.name))],
                  onChanged: (v) => setState(() { parcelId = v; decision = null; }),
                ),
                DropdownButton<String>(
                  value: diseaseCode,
                  hint: const Text('Enfermedad'),
                  items: const [
                    DropdownMenuItem(value: 'repilo', child: Text('Repilo')),
                    DropdownMenuItem(value: 'mildiu', child: Text('Mildiu')),
                  ],
                  onChanged: (v) => setState(() { diseaseCode = v; decision = null; }),
                ),
                FilledButton(onPressed: loading ? null : load, child: const Text('Calcular')),
              ],
            ),
            if (loading) const LinearProgressIndicator(),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'No se pudo calcular la decisión. Revisa la conexión y vuelve a intentarlo.',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            if (decision != null) Expanded(child: _Decision(decision!)),
          ],
        ),
      ),
    );
  }
}

class _Decision extends StatelessWidget {
  const _Decision(this.data);
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final evidence = (data['evidence'] as List<dynamic>? ?? const []).cast<Map<String, dynamic>>();
    final steps = (data['next_steps'] as List<dynamic>? ?? const []).cast<String>();
    return ListView(
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(data['headline']?.toString() ?? '', style: Theme.of(context).textTheme.titleLarge),
              Text('Prioridad: ${data['priority']?.toString() ?? ''} · Puntuación: ${data['decision_score']?.toString() ?? ''}'),
              Text('Confianza: ${data['confidence']?.toString() ?? ''}'),
              const SizedBox(height: 8),
              Text(data['explanation']?.toString() ?? ''),
            ]),
          ),
        ),
        Text('Evidencias', style: Theme.of(context).textTheme.titleLarge),
        ...evidence.map((e) => ListTile(
          leading: const Icon(Icons.fact_check_outlined),
          title: Text(e['key']?.toString() ?? ''),
          subtitle: Text('${e['value']?.toString() ?? ''} · peso ${e['weight']?.toString() ?? ''}'),
        )),
        Text('Siguientes pasos', style: Theme.of(context).textTheme.titleLarge),
        ...steps.map((s) => ListTile(leading: const Icon(Icons.arrow_forward), title: Text(s))),
      ],
    );
  }
}
