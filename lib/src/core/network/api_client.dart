import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

class ParcelConflictException implements Exception {
  const ParcelConflictException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({String? baseUrl})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl ?? const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000'),
          connectTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
          headers: {'Accept': 'application/json'},
        )) {
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async {
      final token = await FirebaseAuth.instance.currentUser?.getIdToken();
      if (token != null) options.headers['Authorization'] = 'Bearer $token';
      handler.next(options);
    }));
  }

  final Dio _dio;

  Future<List<Map<String, dynamic>>> getParcels() async {
    final response = await _dio.get<List<dynamic>>('/api/v1/parcels');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getRisk(String parcelId) async {
    final response = await _dio.get<List<dynamic>>('/api/v1/disease-risk/$parcelId');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> createParcel({
    required String label,
    required double latitude,
    required double longitude,
    required String cropType,
    required String comarca,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/parcels',
      data: {
        'label': label,
        'latitude': latitude,
        'longitude': longitude,
        'crop_type': cropType,
        'comarca': comarca,
      },
    );
    return response.data!;
  }


  Future<Map<String, dynamic>> updateParcel({
    required String parcelId,
    required String label,
    required double latitude,
    required double longitude,
    required String cropType,
    required String comarca,
    required DateTime expectedUpdatedAt,
  }) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/api/v1/parcels/$parcelId',
        queryParameters: {'expected_updated_at': expectedUpdatedAt.toUtc().toIso8601String()},
        data: {
          'label': label,
          'latitude': latitude,
          'longitude': longitude,
          'crop_type': cropType,
          'comarca': comarca,
        },
      );
      return response.data!;
    } on DioException catch (error) {
      if (error.response?.statusCode == 409) {
        throw const ParcelConflictException(
          'La parcela ha cambiado en otro dispositivo. Se ha conservado tu edición local.',
        );
      }
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> getProducts({String? cropType, String? diseaseCode}) async {
    final response = await _dio.get<List<dynamic>>('/api/v1/products', queryParameters: {
      if (cropType != null) 'crop_type': cropType,
      if (diseaseCode != null) 'disease_code': diseaseCode,
    });
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getAlerts({int limit = 100, int offset = 0, String? parcelId}) async {
    final response = await _dio.get<List<dynamic>>(
      '/api/v1/alerts',
      queryParameters: {
        'limit': limit,
        'offset': offset,
        if (parcelId != null) 'parcel_id': parcelId,
      },
    );
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<void> submitFieldReport({required String parcelId, required String type, required String notes, required int count, required double latitude, required double longitude, String? photoUrl, String? reportId}) async {
    await _dio.post('/api/v1/field-reports', data: {'report_id': reportId, 'parcel_id': parcelId, 'type': type, 'notes': notes, 'count': count, 'latitude': latitude, 'longitude': longitude, 'photo_url': photoUrl, 'reported_at': DateTime.now().toUtc().toIso8601String()});
  }

  Future<void> submitRawFieldReport(Map<String, dynamic> report) async {
    await _dio.post('/api/v1/field-reports', data: report);
  }

  Future<List<Map<String, dynamic>>> getDevices(String parcelId) async {
    final response = await _dio.get<List<dynamic>>('/api/v1/devices/$parcelId');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<void> registerDevice({required String parcelId, required String deviceId, required String name, required String deviceType}) async {
    await _dio.post('/api/v1/devices', data: {'parcel_id': parcelId, 'device_id': deviceId, 'name': name, 'device_type': deviceType});
  }

  Future<void> registerPushToken(String token) async {
    await _dio.post('/api/v1/push-tokens', data: {'token': token, 'platform': 'flutter'});
  }

  Future<void> unregisterPushToken(String token) async {
    await _dio.delete('/api/v1/push-tokens/${Uri.encodeComponent(token)}');
  }

  Future<Map<String, dynamic>> getLatestTelemetry(String parcelId) async {
    final response = await _dio.get<Map<String, dynamic>>('/api/v1/telemetry/$parcelId');
    return response.data!;
  }

  Future<Map<String, dynamic>> getWeather(String parcelId) async {
    final response = await _dio.get<Map<String, dynamic>>('/api/v1/weather/$parcelId');
    return response.data!;
  }

  Future<List<Map<String, dynamic>>> getRiskHistory(String parcelId, {int limit = 100, int offset = 0}) async {
    final response = await _dio.get<List<dynamic>>('/api/v1/risk-history/$parcelId', queryParameters: {'limit': limit, 'offset': offset});
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getIntegrationsHealth() async {
    final response = await _dio.get<Map<String, dynamic>>('/health/integrations');
    return response.data!;
  }
}
