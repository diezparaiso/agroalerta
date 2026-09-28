import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../../core/network/api_client.dart';
import 'local_parcel_store.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
final localParcelStoreProvider = Provider<LocalParcelStore>((ref) => LocalParcelStore());

final parcelsProvider = FutureProvider<List<ParcelSummary>>((ref) async {
  final userId = FirebaseAuth.instance.currentUser?.uid ?? 'offline-user';
  final localStore = ref.read(localParcelStoreProvider);
  final localParcels = await localStore.read(userId);
  try {
    final records = await ref.read(apiClientProvider).getParcels();
    final parcels = records.map(ParcelSummary.fromJson).toList();
    await localStore.write(userId, parcels);
    return parcels.isEmpty ? localParcels : parcels;
  } catch (_) {
    return localParcels.isEmpty ? ParcelSummary.demo : localParcels;
  }
});

class ParcelSummary {
  const ParcelSummary({this.id, this.latitude = 37.39, this.longitude = -5.99, required this.name, required this.crop, required this.place, required this.risk});

  final String? id;
  final double latitude;
  final double longitude;
  final String name;
  final String crop;
  final String place;
  final String risk;

  static List<ParcelSummary> get demo => const [
        ParcelSummary(name: 'Olivar de prueba', crop: 'Olivar', place: 'Campina de Sevilla', risk: 'Medio'),
        ParcelSummary(name: 'Vinedo norte', crop: 'Vinedo', place: 'Montilla-Moriles', risk: 'Bajo'),
        ParcelSummary(name: 'Huerta familiar', crop: 'Olivar', place: 'Sierra de Cordoba', risk: 'Bajo'),
      ];

  factory ParcelSummary.fromJson(Map<String, dynamic> json) => ParcelSummary(
      id: json['id'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 37.39,
      longitude: (json['longitude'] as num?)?.toDouble() ?? -5.99,
        name: json['label'] as String? ?? 'Parcela sin nombre',
        crop: json['crop_type'] == 'vinedo' ? 'Vinedo' : 'Olivar',
        place: json['comarca'] as String? ?? 'Andalucia',
        risk: 'Pendiente',
      );

  Map<String, dynamic> toJson() => {'id': id, 'label': name, 'latitude': latitude, 'longitude': longitude, 'crop_type': crop == 'Vinedo' ? 'vinedo' : 'olivar', 'comarca': place};
}
