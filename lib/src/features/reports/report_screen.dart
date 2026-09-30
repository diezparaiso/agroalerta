import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/storage/photo_upload.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import 'offline_report_store.dart';

class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  final notesController = TextEditingController();
  final countController = TextEditingController(text: '0');
  String type = 'sintoma';
  bool sending = false;
  XFile? photo;
  final offlineStore = OfflineReportStore();

  Future<void> submit() async {
    setState(() => sending = true);
    final parcels = await ref.read(parcelsProvider.future);
    final photoUrl = photo == null ? null : await uploadPhoto(photo!.path);
    try {
      await ref.read(apiClientProvider).submitFieldReport(parcelId: parcels.first.id ?? parcels.first.name, type: type, notes: notesController.text, count: int.tryParse(countController.text) ?? 0, latitude: 37.39, longitude: -5.99, photoUrl: photoUrl);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Observacion enviada')));
    } catch (_) {
      await offlineStore.enqueue({'parcel_id': parcels.first.id ?? parcels.first.name, 'type': type, 'notes': notesController.text, 'count': int.tryParse(countController.text) ?? 0, 'latitude': 37.39, 'longitude': -5.99, 'photo_url': photoUrl, 'reported_at': DateTime.now().toUtc().toIso8601String()});
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Guardada para sincronizar cuando haya conexion')));
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  @override
  Widget build(BuildContext context) => AppPage(title: 'Observacion de campo', subtitle: 'Aporta datos para mejorar los avisos de tu zona', child: ListView(children: [DropdownButtonFormField<String>(initialValue: type, decoration: const InputDecoration(labelText: 'Tipo de observacion'), items: const [DropdownMenuItem(value: 'sintoma', child: Text('Sintoma o enfermedad')), DropdownMenuItem(value: 'trampa', child: Text('Captura en trampa'))], onChanged: (value) => setState(() => type = value ?? 'sintoma')), const SizedBox(height: 16), TextField(controller: countController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Numero observado')), const SizedBox(height: 16), TextField(controller: notesController, maxLines: 5, decoration: const InputDecoration(labelText: 'Notas')), const SizedBox(height: 16), OutlinedButton.icon(onPressed: () async { final selected = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 75); if (selected != null) setState(() => photo = selected); }, icon: const Icon(Icons.camera_alt_outlined), label: Text(photo == null ? 'Añadir fotografía' : 'Fotografía añadida')), const SizedBox(height: 20), FilledButton.icon(onPressed: sending ? null : submit, icon: const Icon(Icons.send), label: Text(sending ? 'Enviando...' : 'Enviar observacion'))]));
}
