import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/location/location_service.dart';
import '../../core/storage/photo_upload.dart';
import '../home/home_screen.dart';
import '../parcels/parcel_provider.dart';
import 'offline_report_store.dart';

class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

/// Coordenadas reales resueltas para el envío (nunca inventadas).
class _Coordinates {
  const _Coordinates(this.latitude, this.longitude, this.source);
  final double latitude;
  final double longitude;
  final String source;
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  final notesController = TextEditingController();
  final countController = TextEditingController(text: '0');
  String type = 'sintoma';
  String? parcelKey;
  bool sending = false;
  String? warning;
  String? info;
  XFile? photo;
  final offlineStore = OfflineReportStore();

  /// Política de coordenadas (decisión del usuario 2026-10-05):
  /// 1) ubicación del dispositivo con permiso,
  /// 2) centro de la parcela,
  /// 3) null → aviso en pantalla. Nunca coordenadas inventadas.
  Future<_Coordinates?> _resolveCoordinates(ParcelSummary parcel) async {
    final position = await LocationService().currentPosition();
    if (position != null) {
      return _Coordinates(position.latitude, position.longitude, 'ubicación del dispositivo');
    }
    final latitude = parcel.latitude;
    final longitude = parcel.longitude;
    if (latitude != null && longitude != null) {
      return _Coordinates(latitude, longitude, 'centro de la parcela');
    }
    return null;
  }

  Future<void> submit() async {
    final parcels = await ref.read(parcelsProvider.future);
    if (parcels.isEmpty) {
      setState(() => warning = 'Crea una parcela antes de enviar una observación.');
      return;
    }
    ParcelSummary? chosen;
    for (final parcel in parcels) {
      if ((parcel.id ?? parcel.name) == parcelKey) chosen = parcel;
    }
    final parcel = chosen ?? parcels.first;
    if (parcel.id == null) {
      setState(() => warning = 'La parcela «${parcel.name}» todavía no está sincronizada con el servidor. Espera a que se sincronice para enviar la observación.');
      return;
    }

    setState(() {
      sending = true;
      warning = null;
      info = null;
    });

    final coordinates = await _resolveCoordinates(parcel);
    if (coordinates == null) {
      setState(() {
        sending = false;
        warning = 'No se pueden obtener coordenadas: la ubicación del dispositivo no está disponible y la parcela «${parcel.name}» no tiene coordenadas. '
            'Activa la ubicación o edita la parcela; nunca se envían coordenadas inventadas.';
      });
      return;
    }
    if (coordinates.source != 'ubicación del dispositivo') {
      setState(() => info = 'Ubicación no disponible: se usarán las coordenadas del ${coordinates.source}.');
    }

    String? photoUrl;
    try {
      photoUrl = photo == null ? null : await uploadPhoto(photo!.path);
      await ref.read(apiClientProvider).submitFieldReport(
            parcelId: parcel.id!,
            type: type,
            notes: notesController.text,
            count: int.tryParse(countController.text) ?? 0,
            latitude: coordinates.latitude,
            longitude: coordinates.longitude,
            photoUrl: photoUrl,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Observación enviada')));
      }
    } catch (_) {
      await offlineStore.enqueue({
        'parcel_id': parcel.id,
        'type': type,
        'notes': notesController.text,
        'count': int.tryParse(countController.text) ?? 0,
        'latitude': coordinates.latitude,
        'longitude': coordinates.longitude,
        'photo_url': photoUrl,
        'reported_at': DateTime.now().toUtc().toIso8601String(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Guardada para sincronizar cuando haya conexión')),
        );
      }
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final parcels = ref.watch(parcelsProvider);
    return AppPage(
      title: 'Observación de campo',
      subtitle: 'Aporta datos para mejorar los avisos de tu zona',
      child: parcels.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('No se pudieron cargar las parcelas: $error')),
        data: (items) => ListView(
          children: [
            if (items.isEmpty)
              const Padding(
                padding: EdgeInsets.only(bottom: 16),
                child: Text('Crea una parcela antes de enviar una observación.'),
              )
            else ...[
              DropdownButtonFormField<String>(
                initialValue: parcelKey ?? (items.first.id ?? items.first.name),
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Parcela'),
                items: [
                  for (final parcel in items)
                    DropdownMenuItem(
                      value: parcel.id ?? parcel.name,
                      enabled: parcel.id != null,
                      child: Text(parcel.id == null ? '${parcel.name} (sin sincronizar)' : parcel.name),
                    ),
                ],
                onChanged: (value) => setState(() => parcelKey = value),
              ),
              const SizedBox(height: 16),
            ],
            DropdownButtonFormField<String>(
              initialValue: type,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Tipo de observación'),
              items: const [
                DropdownMenuItem(value: 'sintoma', child: Text('Síntoma o enfermedad')),
                DropdownMenuItem(value: 'trampa', child: Text('Captura en trampa')),
              ],
              onChanged: (value) => setState(() => type = value ?? 'sintoma'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: countController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Número observado'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: notesController,
              maxLines: 5,
              decoration: const InputDecoration(labelText: 'Notas'),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () async {
                final selected = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 75);
                if (selected != null) setState(() => photo = selected);
              },
              icon: const Icon(Icons.camera_alt_outlined),
              label: Text(photo == null ? 'Añadir fotografía' : 'Fotografía añadida'),
            ),
            const SizedBox(height: 12),
            const Text(
              'La ubicación se toma de tu dispositivo con tu permiso; si no está disponible se usa el centro de la parcela.',
              style: TextStyle(fontSize: 12),
            ),
            if (info != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(info!, style: TextStyle(color: Theme.of(context).colorScheme.primary)),
              ),
            if (warning != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(warning!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: sending ? null : submit,
              icon: const Icon(Icons.send),
              label: Text(sending ? 'Enviando...' : 'Enviar observación'),
            ),
          ],
        ),
      ),
    );
  }
}
