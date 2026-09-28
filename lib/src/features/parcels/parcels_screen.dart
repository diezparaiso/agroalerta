import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../home/home_screen.dart';
import '../../core/location/location_service.dart';
import 'parcel_provider.dart';
import '../../core/network/api_client.dart';
import 'parcel_conflict.dart';

class ParcelsScreen extends ConsumerWidget {
  const ParcelsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPage(title: 'Parcelas', subtitle: 'Gestiona los puntos que quieres monitorizar', actions: [FilledButton.icon(onPressed: () => _showCreateDialog(context, ref), icon: const Icon(Icons.add), label: const Text('Nueva parcela'))], child: ref.watch(parcelsProvider).when(data: (parcels) => LayoutBuilder(builder: (context, constraints) { final columns = constraints.maxWidth > 900 ? 3 : constraints.maxWidth > 560 ? 2 : 1; return GridView.count(crossAxisCount: columns, crossAxisSpacing: 16, mainAxisSpacing: 16, childAspectRatio: 1.45, children: [for (final parcel in parcels) _ParcelCard(parcel: parcel, ref: ref)]); }), loading: () => const Center(child: CircularProgressIndicator()), error: (error, stack) => Center(child: Text('No se pudieron cargar las parcelas: $error'))));
}

Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
  final labelController = TextEditingController();
  final comarcaController = TextEditingController();
  final latitudeController = TextEditingController(text: '0');
  final longitudeController = TextEditingController(text: '0');
  var cropType = 'olivar';
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(builder: (context, setState) => AlertDialog(
      title: const Text('Nueva parcela'),
      content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: labelController, decoration: const InputDecoration(labelText: 'Nombre')),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(initialValue: cropType, decoration: const InputDecoration(labelText: 'Cultivo'), items: const [DropdownMenuItem(value: 'olivar', child: Text('Olivar')), DropdownMenuItem(value: 'vinedo', child: Text('Vinedo'))], onChanged: (value) => setState(() => cropType = value ?? 'olivar')),
        const SizedBox(height: 12),
        TextField(controller: comarcaController, decoration: const InputDecoration(labelText: 'Comarca')),
        const SizedBox(height: 12),
        OutlinedButton.icon(onPressed: () async { final position = await LocationService().currentPosition(); if (position != null) { setState(() { latitudeController.text = position.latitude.toStringAsFixed(6); longitudeController.text = position.longitude.toStringAsFixed(6); }); } }, icon: const Icon(Icons.my_location), label: const Text('Usar mi ubicacion actual')),
        const SizedBox(height: 12),
        Row(children: [Expanded(child: TextField(controller: latitudeController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Latitud'))), const SizedBox(width: 8), Expanded(child: TextField(controller: longitudeController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Longitud')))]),
      ])),
      actions: [TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')), FilledButton(onPressed: () async { if (labelController.text.trim().isEmpty || comarcaController.text.trim().isEmpty) return; final parcel = ParcelSummary(name: labelController.text.trim(), crop: cropType == 'vinedo' ? 'Vinedo' : 'Olivar', place: comarcaController.text.trim(), risk: 'Pendiente'); final userId = FirebaseAuth.instance.currentUser?.uid ?? 'offline-user'; final userParcels = await ref.read(localParcelStoreProvider).read(userId); await ref.read(localParcelStoreProvider).write(userId, [...userParcels, parcel]); try { await ref.read(apiClientProvider).createParcel(label: labelController.text.trim(), latitude: double.tryParse(latitudeController.text) ?? 0, longitude: double.tryParse(longitudeController.text) ?? 0, cropType: cropType, comarca: comarcaController.text.trim()); } catch (_) {} ref.invalidate(parcelsProvider); if (dialogContext.mounted) Navigator.pop(dialogContext); }, child: const Text('Guardar'))],
    )),
  );
}

class _ParcelCard extends StatelessWidget {
  const _ParcelCard({required this.parcel, required this.ref});
  final ParcelSummary parcel;
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.landscape_outlined, size: 30),
        const Spacer(),
        Text(parcel.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
        Text('${parcel.crop} · ${parcel.place}'),
        const SizedBox(height: 10),
        Row(children: [
          const Icon(Icons.circle, size: 10, color: Colors.amber),
          const SizedBox(width: 8),
          Text('Riesgo ${parcel.risk}'),
          const Spacer(),
          IconButton(
            tooltip: 'Editar parcela',
            onPressed: () => _editParcel(context, ref, parcel),
            icon: const Icon(Icons.edit_outlined),
          ),
        ]),
      ]),
    ),
  );
}

Future<void> _editParcel(BuildContext context, WidgetRef ref, ParcelSummary parcel) async {
  final labelController = TextEditingController(text: parcel.name);
  try {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Editar parcela'),
        content: TextField(controller: labelController, decoration: const InputDecoration(labelText: 'Nombre')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () async {
              try {
                await updateParcelWithConflictProtection(
                  apiClient: ref.read(apiClientProvider),
                  parcel: parcel,
                  label: labelController.text.trim(),
                );
                if (dialogContext.mounted) Navigator.pop(dialogContext);
                ref.invalidate(parcelsProvider);
              } on ParcelConflictException {
                if (dialogContext.mounted) Navigator.pop(dialogContext);
                if (context.mounted) await _showParcelConflict(context, ref, parcel, labelController.text.trim());
              } catch (error) {
                if (dialogContext.mounted) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    SnackBar(content: Text('No se pudo actualizar la parcela: $error')),
                  );
                }
              }
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
  } finally {
    labelController.dispose();
  }
}

Future<void> _showParcelConflict(
  BuildContext context,
  WidgetRef ref,
  ParcelSummary local,
  String localLabel,
) async {
  final items = await ref.read(apiClientProvider).getParcels();
  final remoteList = items.map(ParcelSummary.fromJson).where((item) => item.id == local.id).toList();
  if (remoteList.isEmpty || !context.mounted) return;
  final remote = remoteList.first;

  final choice = await showDialog<ParcelConflictChoice>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('La parcela cambió'),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Otro dispositivo modificó esta parcela.'),
        const SizedBox(height: 12),
        Text('Tu edición: $localLabel'),
        Text('Servidor: ${remote.name}'),
        Text('Cultivo servidor: ${remote.crop}'),
        Text('Comarca servidor: ${remote.place}'),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(dialogContext, ParcelConflictChoice.cancel), child: const Text('Cancelar')),
        TextButton(onPressed: () => Navigator.pop(dialogContext, ParcelConflictChoice.useRemote), child: const Text('Usar servidor')),
        FilledButton(onPressed: () => Navigator.pop(dialogContext, ParcelConflictChoice.keepLocal), child: const Text('Conservar mi edición')),
      ],
    ),
  );

  if (!context.mounted || choice == null || choice == ParcelConflictChoice.cancel) return;
  if (choice == ParcelConflictChoice.useRemote) {
    ref.invalidate(parcelsProvider);
    return;
  }

  try {
    await updateParcelWithConflictProtection(
      apiClient: ref.read(apiClientProvider),
      parcel: remote,
      label: localLabel,
    );
    ref.invalidate(parcelsProvider);
  } on ParcelConflictException {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('La parcela volvió a cambiar. Recarga antes de intentarlo de nuevo.')),
      );
    }
  }
}
