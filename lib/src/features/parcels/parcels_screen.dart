import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:go_router/go_router.dart';

import '../home/home_screen.dart';
import '../../core/location/location_service.dart';
import 'parcel_provider.dart';

class ParcelsScreen extends ConsumerWidget {
  const ParcelsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPage(title: 'Parcelas', subtitle: 'Gestiona los puntos que quieres monitorizar', actions: [OutlinedButton.icon(onPressed: () => context.go('/parcels/sigpac'), icon: const Icon(Icons.map_outlined), label: const Text('Importar desde SIGPAC')), FilledButton.icon(onPressed: () => _showCreateDialog(context, ref), icon: const Icon(Icons.add), label: const Text('Nueva parcela'))], child: ref.watch(parcelsProvider).when(data: (parcels) => LayoutBuilder(builder: (context, constraints) { final columns = constraints.maxWidth > 900 ? 3 : constraints.maxWidth > 560 ? 2 : 1; return GridView.count(crossAxisCount: columns, crossAxisSpacing: 16, mainAxisSpacing: 16, childAspectRatio: 1.45, children: [for (final parcel in parcels) _ParcelCard(name: parcel.name, crop: parcel.crop, place: parcel.place, risk: parcel.risk)]); }), loading: () => const Center(child: CircularProgressIndicator()), error: (error, stack) => Center(child: Text('No se pudieron cargar las parcelas: $error'))));
}

Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
  final labelController = TextEditingController();
  final comarcaController = TextEditingController();
  final latitudeController = TextEditingController(text: '37.39');
  final longitudeController = TextEditingController(text: '-5.99');
  var cropType = 'olivar';
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(builder: (context, setState) => AlertDialog(
      title: const Text('Nueva parcela'),
      content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: labelController, decoration: const InputDecoration(labelText: 'Nombre')),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(initialValue: cropType, decoration: const InputDecoration(labelText: 'Cultivo'), items: const [DropdownMenuItem(value: 'olivar', child: Text('Olivar')), DropdownMenuItem(value: 'viñedo', child: Text('Viñedo'))], onChanged: (value) => setState(() => cropType = value ?? 'olivar')),
        const SizedBox(height: 12),
        TextField(controller: comarcaController, decoration: const InputDecoration(labelText: 'Comarca')),
        const SizedBox(height: 12),
        OutlinedButton.icon(onPressed: () async { final position = await LocationService().currentPosition(); if (position != null) { setState(() { latitudeController.text = position.latitude.toStringAsFixed(6); longitudeController.text = position.longitude.toStringAsFixed(6); }); } }, icon: const Icon(Icons.my_location), label: const Text('Usar mi ubicación actual')),
        const SizedBox(height: 12),
        Row(children: [Expanded(child: TextField(controller: latitudeController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Latitud'))), const SizedBox(width: 8), Expanded(child: TextField(controller: longitudeController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Longitud')))]),
      ])),
      actions: [TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')), FilledButton(onPressed: () async { if (labelController.text.trim().isEmpty || comarcaController.text.trim().isEmpty) return; final parcel = ParcelSummary(name: labelController.text.trim(), crop: cropType == 'vinedo' ? 'Vinedo' : 'Olivar', place: comarcaController.text.trim(), risk: 'Pendiente'); final userId = FirebaseAuth.instance.currentUser?.uid ?? 'offline-user'; final userParcels = await ref.read(localParcelStoreProvider).read(userId); await ref.read(localParcelStoreProvider).write(userId, [...userParcels, parcel]); try { await ref.read(apiClientProvider).createParcel(label: labelController.text.trim(), latitude: double.tryParse(latitudeController.text) ?? 37.39, longitude: double.tryParse(longitudeController.text) ?? -5.99, cropType: cropType, comarca: comarcaController.text.trim()); } catch (_) {} ref.invalidate(parcelsProvider); if (dialogContext.mounted) Navigator.pop(dialogContext); }, child: const Text('Guardar'))],
    )),
  );
}

class _ParcelCard extends StatelessWidget {
  const _ParcelCard({required this.name, required this.crop, required this.place, required this.risk});
  final String name, crop, place, risk;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.landscape_outlined, size: 30), const Spacer(), Text(name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)), Text('$crop · $place'), const SizedBox(height: 10), Row(children: [const Icon(Icons.circle, size: 10, color: Colors.amber), const SizedBox(width: 8), Text('Riesgo $risk')])])));
}
