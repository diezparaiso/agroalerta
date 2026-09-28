import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import '../../core/network/api_client.dart';
import 'campaigns_provider.dart';

class CampaignsScreen extends ConsumerWidget {
  const CampaignsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final parcels = ref.watch(parcelsProvider);
    final selected = ref.watch(selectedCampaignParcelProvider);

    return AppPage(
      title: 'Campañas',
      subtitle: 'Gestiona el ciclo temporal de cada parcela',
      actions: [
        FilledButton.icon(
          onPressed: selected == null ? null : () => _showCreateCampaign(context, ref, selected),
          icon: const Icon(Icons.add),
          label: const Text('Nueva campaña'),
        ),
      ],
      child: parcels.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('No se pudieron cargar las parcelas: $error')),
        data: (items) {
          final current = items.where((item) => item.id == selected).firstOrNull;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DropdownButton<String>(
                value: current?.id,
                hint: const Text('Selecciona una parcela'),
                items: [
                  for (final parcel in items)
                    DropdownMenuItem(value: parcel.id, child: Text(parcel.name)),
                ],
                onChanged: (value) => ref.read(selectedCampaignParcelProvider.notifier).state = value,
              ),
              const SizedBox(height: 12),
              Expanded(child: ref.watch(campaignsProvider).when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, _) => Center(child: Text('No se pudieron cargar las campañas: $error')),
                data: (campaigns) => campaigns.isEmpty
                    ? const Center(child: Text('No hay campañas para esta parcela.'))
                    : ListView.separated(
                        itemCount: campaigns.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (context, index) => _CampaignCard(
                          campaign: campaigns[index],
                          onChanged: () => ref.invalidate(campaignsProvider),
                        ),
                      ),
              )),
            ],
          );
        },
      ),
    );
  }
}

class _CampaignCard extends ConsumerWidget {
  const _CampaignCard({required this.campaign, required this.onChanged});
  final Map<String, dynamic> campaign;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = '${campaign['status'] ?? 'planned'}';
    return Card(
      child: ListTile(
        leading: const Icon(Icons.agriculture_outlined),
        title: Text('${campaign['season_label'] ?? 'Campaña'}'),
        subtitle: Text(
          '${campaign['crop_type'] ?? ''} · ${campaign['variety'] ?? 'variedad no indicada'}\n'
          'Estado: $status · Inicio: ${campaign['started_at'] ?? ''}',
        ),
        isThreeLine: true,
        trailing: Wrap(spacing: 4, children: [
          IconButton(
            tooltip: 'Resultados',
            onPressed: () => _showResults(context, ref, '${campaign['id']}', '${campaign['season_label'] ?? 'Campaña'}'),
            icon: const Icon(Icons.analytics_outlined),
          ),
          PopupMenuButton<String>(
          onSelected: (value) async {
            await ref.read(apiClientProvider).updateCampaignStatus(
              campaignId: '${campaign['id']}',
              status: value,
            );
            onChanged();
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'active', child: Text('Activar')),
            PopupMenuItem(value: 'closed', child: Text('Cerrar')),
            PopupMenuItem(value: 'cancelled', child: Text('Cancelar')),
          ],
          ),
        ]),
      ),
    );
  }
}

Future<void> _showResults(BuildContext context, WidgetRef ref, String campaignId, String seasonLabel) async {
  final summary = await ref.read(apiClientProvider).getCampaignResultsSummary(campaignId);
  if (!context.mounted) return;
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text('Resultados · $seasonLabel'),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Producción: ${summary['harvested_quantity_kg'] ?? 0} kg'),
        Text('Superficie productiva: ${summary['productive_area_ha'] ?? 0} ha'),
        Text('Rendimiento: ${summary['yield_kg_ha'] ?? '--'} kg/ha'),
        Text('Objetivo: ${summary['target_yield_kg_ha'] ?? '--'} kg/ha'),
        Text('Desviación: ${summary['target_deviation_pct'] ?? '--'} %'),
        const SizedBox(height: 10),
        Text('Decisiones registradas: ${summary['decision_count'] ?? 0}'),
        Text('Actividades: ${summary['activity_count'] ?? 0}'),
      ]),
      actions: [TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cerrar'))],
    ),
  );
}

Future<void> _showCreateCampaign(BuildContext context, WidgetRef ref, String parcelId) async {
  final season = TextEditingController();
  final variety = TextEditingController();
  final target = TextEditingController();
  final notes = TextEditingController();
  final parcels = ref.read(parcelsProvider).value ?? const [];
  final parcel = parcels.where((item) => item.id == parcelId).firstOrNull;
  if (parcel == null) return;

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Nueva campaña'),
      content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: season, decoration: const InputDecoration(labelText: 'Temporada')),
        TextField(controller: variety, decoration: const InputDecoration(labelText: 'Variedad')),
        TextField(controller: target, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Objetivo t/ha')),
        TextField(controller: notes, decoration: const InputDecoration(labelText: 'Notas')),
      ])),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')),
        FilledButton(
          onPressed: () async {
            if (season.text.trim().isEmpty) return;
            await ref.read(apiClientProvider).createCampaign(
              parcelId: parcelId,
              cropType: parcel.crop == 'Vinedo' ? 'vinedo' : 'olivar',
              seasonLabel: season.text.trim(),
              startedAt: DateTime.now(),
              variety: variety.text.trim().isEmpty ? null : variety.text.trim(),
              targetYieldTHa: double.tryParse(target.text),
              notes: notes.text.trim().isEmpty ? null : notes.text.trim(),
            );
            ref.invalidate(campaignsProvider);
            if (dialogContext.mounted) Navigator.pop(dialogContext);
          },
          child: const Text('Crear'),
        ),
      ],
    ),
  );
}
