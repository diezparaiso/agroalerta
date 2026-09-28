import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/storage/photo_upload.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import 'offline_report_store.dart';
import 'offline_queue_status_provider.dart';
import 'report_payload.dart';

class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  final notesController = TextEditingController();
  final countController = TextEditingController(text: '0');
  String type = 'sintoma';
  String? selectedParcelId;
  bool sending = false;
  XFile? photo;
  final offlineStore = OfflineReportStore();

  Future<void> submit() async {
    setState(() => sending = true);
    final parcels = await ref.read(parcelsProvider.future);
    if (parcels.isEmpty) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Añade una parcela antes de enviar una observación')));
      if (mounted) setState(() => sending = false);
      return;
    }

    final selectedId = selectedParcelId;
    final matching = selectedId == null
        ? null
        : parcels.where((parcel) => parcel.id == selectedId);
    final parcel = matching == null || matching.isEmpty ? null : matching.first;
    if (parcel == null) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Selecciona una parcela antes de enviar la observación')));
      if (mounted) setState(() => sending = false);
      return;
    }

    final photoUrl = photo == null ? null : await uploadPhoto(photo!.path);
    final payload = buildFieldReportPayload(
      parcel: parcel,
      type: type,
      notes: notesController.text,
      count: int.tryParse(countController.text) ?? 0,
      photoUrl: photoUrl,
    );
    try {
      await ref.read(apiClientProvider).submitFieldReport(
        parcelId: payload['parcel_id'] as String,
        type: payload['type'] as String,
        notes: payload['notes'] as String,
        count: payload['count'] as int,
        latitude: payload['latitude'] as double,
        longitude: payload['longitude'] as double,
        photoUrl: payload['photo_url'] as String?,
      );
      ref.invalidate(offlineQueueStatusProvider);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Observacion enviada')));
    } catch (_) {
      await offlineStore.enqueue(payload);
      ref.invalidate(offlineQueueStatusProvider);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Guardada para sincronizar cuando haya conexion')));
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final parcelsAsync = ref.watch(parcelsProvider);
    final queueStatusAsync = ref.watch(offlineQueueStatusProvider);

    return AppPage(
      title: 'Observacion de campo',
      subtitle: 'Aporta datos para mejorar los avisos de tu zona',
      child: ListView(
        children: [
          queueStatusAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => const SizedBox.shrink(),
            data: (status) {
              if (!status.hasPending) {
                return const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.cloud_done_outlined),
                  title: Text('Sin observaciones pendientes'),
                );
              }
              final next = status.nextAttemptAt;
              final detail = next == null
                  ? 'Pendientes de sincronizar'
                  : 'Próximo reintento: ${next.hour.toString().padLeft(2, '0')}:${next.minute.toString().padLeft(2, '0')}';
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.cloud_upload_outlined),
                title: Text('${status.pendingCount} observación(es) pendientes'),
                subtitle: Text(status.failedCount == 0 ? detail : '$detail · ${status.failedCount} con reintento'),
              );
            },
          ),

          parcelsAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => const Text('No se pueden cargar las parcelas'),
            data: (parcels) {
              final validIds = parcels.map((parcel) => parcel.id).whereType<String>().toSet();
              final value = validIds.contains(selectedParcelId) ? selectedParcelId : null;
              return DropdownButtonFormField<String>(
                initialValue: value,
                decoration: const InputDecoration(labelText: 'Parcela'),
                items: [
                  for (final parcel in parcels)
                    if (parcel.id != null)
                      DropdownMenuItem(value: parcel.id, child: Text(parcel.name)),
                ],
                onChanged: sending ? null : (value) => setState(() => selectedParcelId = value),
              );
            },
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: type,
            decoration: const InputDecoration(labelText: 'Tipo de observacion'),
            items: const [
              DropdownMenuItem(value: 'sintoma', child: Text('Sintoma o enfermedad')),
              DropdownMenuItem(value: 'trampa', child: Text('Captura en trampa')),
            ],
            onChanged: (value) => setState(() => type = value ?? 'sintoma'),
          ),
          const SizedBox(height: 16),
          TextField(controller: countController, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Numero observado')),
          const SizedBox(height: 16),
          TextField(controller: notesController, maxLines: 5, decoration: const InputDecoration(labelText: 'Notas')),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () async {
              final selected = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 75);
              if (selected != null) setState(() => photo = selected);
            },
            icon: const Icon(Icons.camera_alt_outlined),
            label: Text(photo == null ? 'Añadir fotografía' : 'Fotografía añadida'),
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: sending ? null : submit,
            icon: const Icon(Icons.send),
            label: Text(sending ? 'Enviando...' : 'Enviar observacion'),
          ),
        ],
      ),
    );
  }
}
