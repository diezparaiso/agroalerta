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
    if (localParcels.isNotEmpty) return localParcels;
    rethrow;
  }
});

class ParcelSummary {
  const ParcelSummary({this.id, this.latitude, this.longitude, required this.name, required this.crop, required this.place, required this.risk});

  final String? id;

  /// Coordenadas reales de la parcela. `null` cuando el servidor no las
  /// devuelve: nunca se rellenan con valores inventados.
  final double? latitude;
  final double? longitude;
  final String name;
  final String crop;
  final String place;
  final String risk;

  factory ParcelSummary.fromJson(Map<String, dynamic> json) => ParcelSummary(
      id: json['id'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
        name: json['label'] as String? ?? 'Parcela sin nombre',
        crop: json['crop_type'] == 'vinedo' ? 'Vinedo' : 'Olivar',
        place: json['comarca'] as String? ?? 'Andalucia',
        risk: 'Pendiente',
      );

  Map<String, dynamic> toJson() => {'id': id, 'label': name, 'latitude': latitude, 'longitude': longitude, 'crop_type': crop == 'Vinedo' ? 'vinedo' : 'olivar', 'comarca': place};
}
