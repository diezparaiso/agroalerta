import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'parcel_provider.dart';

class ParcelMapPreview extends ConsumerWidget {
  const ParcelMapPreview({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final parcels = ref.watch(parcelsProvider).value ?? const <ParcelSummary>[];
    final validParcels = parcels.where((parcel) {
      return parcel.latitude != 0 && parcel.longitude != 0;
    }).toList();

    final center = validParcels.isEmpty
        ? const LatLng(0, 0)
        : LatLng(
            validParcels.map((parcel) => parcel.latitude).reduce((a, b) => a + b) / validParcels.length,
            validParcels.map((parcel) => parcel.longitude).reduce((a, b) => a + b) / validParcels.length,
          );

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Stack(
        children: [
          FlutterMap(
            options: MapOptions(
              initialCenter: center,
              initialZoom: validParcels.isEmpty ? 2 : 10,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.agrotech.agroalerta',
              ),
              MarkerLayer(
                markers: [
                  for (final parcel in validParcels)
                    Marker(
                      point: LatLng(parcel.latitude, parcel.longitude),
                      width: 44,
                      height: 44,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.primary,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Theme.of(context).colorScheme.surface,
                            width: 3,
                          ),
                        ),
                        child: Icon(
                          Icons.agriculture,
                          color: Theme.of(context).colorScheme.onPrimary,
                          size: 22,
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
          if (validParcels.isEmpty)
            Positioned.fill(
              child: ColoredBox(
                color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.82),
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Text(
                      'Mapa pendiente de coordenadas de parcela',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
