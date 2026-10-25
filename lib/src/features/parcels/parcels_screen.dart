import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/location/location_service.dart';
import '../../core/ui/error_view.dart';
import '../home/home_screen.dart';
import 'parcel_provider.dart';

class ParcelsScreen extends ConsumerWidget {
  const ParcelsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppPage(
      title: 'Parcelas',
      subtitle: 'Gestiona los puntos que quieres monitorizar',
      actions: [
        FilledButton.icon(
          onPressed: () => _showCreateDialog(context, ref),
          icon: const Icon(Icons.add),
          label: const Text('Nueva parcela'),
        ),
      ],
      child: ref.watch(parcelsProvider).when(
            data: (parcels) => LayoutBuilder(
              builder: (context, constraints) {
                final columns = constraints.maxWidth > 900
                    ? 3
                    : constraints.maxWidth > 560
                        ? 2
                        : 1;
                return GridView.count(
                  crossAxisCount: columns,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 1.45,
                  children: [
                    for (final parcel in parcels)
                      _ParcelCard(
                        name: parcel.name,
                        crop: parcel.crop,
                        place: parcel.place,
                        risk: parcel.risk,
                      ),
                  ],
                );
              },
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => ErrorView(
              message: 'No se pudieron cargar las parcelas.',
              onRetry: () => ref.invalidate(parcelsProvider),
            ),
          ),
    );
  }
}

Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
  final labelController = TextEditingController();
  final comarcaController = TextEditingController();
  final latitudeController = TextEditingController();
  final longitudeController = TextEditingController();
  var cropType = 'olivar';

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (context, setState) {
        String? errorText;

        void setError(String message) => setState(() => errorText = message);

        return AlertDialog(
          title: const Text('Nueva parcela'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: labelController,
                  decoration: const InputDecoration(labelText: 'Nombre'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: cropType,
                  decoration: const InputDecoration(labelText: 'Cultivo'),
                  items: const [
                    DropdownMenuItem(value: 'olivar', child: Text('Olivar')),
                    DropdownMenuItem(value: 'vinedo', child: Text('Viñedo')),
                  ],
                  onChanged: (value) =>
                      setState(() => cropType = value ?? 'olivar'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: comarcaController,
                  decoration: const InputDecoration(labelText: 'Comarca'),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () async {
                    final position = await LocationService().currentPosition();
                    if (position != null) {
                      setState(() {
                        latitudeController.text =
                            position.latitude.toStringAsFixed(6);
                        longitudeController.text =
                            position.longitude.toStringAsFixed(6);
                        errorText = null;
                      });
                    } else {
                      setError(
                          'No se pudo obtener tu ubicación. Revisa el permiso de localización o introduce las coordenadas manualmente.');
                    }
                  },
                  icon: const Icon(Icons.my_location),
                  label: const Text('Usar mi ubicación actual'),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: latitudeController,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                          signed: true,
                        ),
                        decoration: const InputDecoration(labelText: 'Latitud'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: longitudeController,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                          signed: true,
                        ),
                        decoration:
                            const InputDecoration(labelText: 'Longitud'),
                      ),
                    ),
                  ],
                ),
                if (errorText != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(
                      errorText!,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error),
                    ),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () async {
                if (labelController.text.trim().isEmpty ||
                    comarcaController.text.trim().isEmpty) {
                  setError('El nombre y la comarca son obligatorios.');
                  return;
                }
                final latitude = double.tryParse(latitudeController.text);
                final longitude = double.tryParse(longitudeController.text);
                if (latitude == null || longitude == null) {
                  setError(
                      'Introduce latitud y longitud válidas o usa tu ubicación actual: no se guardan coordenadas inventadas.');
                  return;
                }

                final parcel = ParcelSummary(
                  latitude: latitude,
                  longitude: longitude,
                  name: labelController.text.trim(),
                  crop: cropType == 'vinedo' ? 'Viñedo' : 'Olivar',
                  place: comarcaController.text.trim(),
                  risk: 'Pendiente',
                );
                final userId =
                    FirebaseAuth.instance.currentUser?.uid ?? 'offline-user';
                final userParcels =
                    await ref.read(localParcelStoreProvider).read(userId);
                await ref
                    .read(localParcelStoreProvider)
                    .write(userId, [...userParcels, parcel]);

                try {
                  await ref.read(apiClientProvider).createParcel(
                        label: labelController.text.trim(),
                        latitude: latitude,
                        longitude: longitude,
                        cropType: cropType,
                        comarca: comarcaController.text.trim(),
                      );
                } catch (_) {}

                ref.invalidate(parcelsProvider);
                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext);
                }
              },
              child: const Text('Guardar'),
            ),
          ],
        );
      },
    ),
  );
}

class _ParcelCard extends StatelessWidget {
  const _ParcelCard({
    required this.name,
    required this.crop,
    required this.place,
    required this.risk,
  });

  final String name;
  final String crop;
  final String place;
  final String risk;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.landscape_outlined, size: 30),
            const Spacer(),
            Text(
              name,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 18,
              ),
            ),
            Text('$crop · $place'),
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(Icons.circle, size: 10, color: Colors.amber),
                const SizedBox(width: 8),
                Text('Riesgo $risk'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
