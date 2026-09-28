import 'package:uuid/uuid.dart';

import '../parcels/parcel_provider.dart';

Map<String, dynamic> buildFieldReportPayload({
  required ParcelSummary parcel,
  required String type,
  required String notes,
  required int count,
  required String? photoUrl,
}) {
  if (parcel.id == null || (parcel.latitude == 0 && parcel.longitude == 0)) {
    throw ArgumentError('La parcela debe tener identificador y coordenadas válidas');
  }

  return {
    'report_id': const Uuid().v4(),
    'parcel_id': parcel.id!,
    'type': type,
    'notes': notes,
    'count': count,
    'latitude': parcel.latitude,
    'longitude': parcel.longitude,
    'photo_url': photoUrl,
    'reported_at': DateTime.now().toUtc().toIso8601String(),
  };
}
