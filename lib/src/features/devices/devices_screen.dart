import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';

final devicesProvider = FutureProvider.family<List<Map<String, dynamic>>, String>((ref, parcelId) => ref.read(apiClientProvider).getDevices(parcelId));

class DevicesScreen extends ConsumerWidget {
  const DevicesScreen({required this.parcelId, super.key});
  final String parcelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPage(title: 'Sensores IoT', subtitle: 'Parcela $parcelId', child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [Align(alignment: Alignment.centerRight, child: FilledButton.icon(onPressed: () => _register(context, ref), icon: const Icon(Icons.add), label: const Text('Registrar sensor'))), const SizedBox(height: 16), Expanded(child: ref.watch(devicesProvider(parcelId)).when(data: (devices) => devices.isEmpty ? const Center(child: Text('No hay sensores registrados')) : ListView(children: [for (final device in devices) Card(child: ListTile(leading: const Icon(Icons.sensors_outlined), title: Text(device['name'] as String? ?? 'Sensor'), subtitle: Text('${device['device_type']} · ${device['device_id']}'), trailing: const Icon(Icons.circle, size: 12, color: Colors.green)))]), loading: () => const Center(child: CircularProgressIndicator()), error: (error, stack) => Center(child: Text('No se pudieron cargar los sensores: $error'))))]));

  Future<void> _register(BuildContext context, WidgetRef ref) async {
    final id = TextEditingController();
    final name = TextEditingController();
    var type = 'weather_station';
    await showDialog<void>(context: context, builder: (dialogContext) => StatefulBuilder(builder: (context, setState) => AlertDialog(title: const Text('Registrar sensor'), content: Column(mainAxisSize: MainAxisSize.min, children: [TextField(controller: id, decoration: const InputDecoration(labelText: 'Identificador')), TextField(controller: name, decoration: const InputDecoration(labelText: 'Nombre')), DropdownButtonFormField<String>(value: type, items: const [DropdownMenuItem(value: 'weather_station', child: Text('Estacion meteorologica')), DropdownMenuItem(value: 'leaf_sensor', child: Text('Sensor de hoja')), DropdownMenuItem(value: 'soil_sensor', child: Text('Sensor de suelo'))], onChanged: (value) => setState(() => type = value ?? type))]), actions: [TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')), FilledButton(onPressed: () async { await ref.read(apiClientProvider).registerDevice(parcelId: parcelId, deviceId: id.text, name: name.text, deviceType: type); ref.invalidate(devicesProvider(parcelId)); if (dialogContext.mounted) Navigator.pop(dialogContext); }, child: const Text('Guardar'))])));
  }
}
