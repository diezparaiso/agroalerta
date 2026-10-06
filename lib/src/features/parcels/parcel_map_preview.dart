import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'parcel_provider.dart';

class ParcelMapPreview extends ConsumerWidget {
  const ParcelMapPreview({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: FlutterMap(
          options: const MapOptions(initialCenter: LatLng(37.39, -5.99), initialZoom: 8.5),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.agrotech.agroalerta',
            ),
            MarkerLayer(markers: [
              for (final parcel in ref.watch(parcelsProvider).value ?? const <ParcelSummary>[])
                if (parcel.latitude != null && parcel.longitude != null)
                  Marker(point: LatLng(parcel.latitude!, parcel.longitude!), width: 44, height: 44, child: const Icon(Icons.location_pin, color: Colors.red, size: 40)),
            ]),
          ],
        ),
      );
}
