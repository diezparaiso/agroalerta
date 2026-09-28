import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

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

  Future<List<Map<String, dynamic>>> getProducts() async {
    final response = await _dio.get<List<dynamic>>('/api/v1/products');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getAlerts() async {
    final response = await _dio.get<List<dynamic>>('/api/v1/alerts');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<void> submitFieldReport({required String parcelId, required String type, required String notes, required int count, required double latitude, required double longitude, String? photoUrl}) async {
    await _dio.post('/api/v1/field-reports', data: {'parcel_id': parcelId, 'type': type, 'notes': notes, 'count': count, 'latitude': latitude, 'longitude': longitude, 'photo_url': photoUrl, 'reported_at': DateTime.now().toUtc().toIso8601String()});
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

  Future<List<Map<String, dynamic>>> getActivityTimeline(String parcelId, {int limit = 100}) async {
    final response = await _dio.get<List<dynamic>>(
      '/api/v1/parcels/$parcelId/activity-timeline',
      queryParameters: {'limit': limit},
    );
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getDecisions(String parcelId, String diseaseCode, {String? campaignId}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/agronomic-decision/$parcelId/$diseaseCode',
      queryParameters: campaignId == null ? null : {'campaign_id': campaignId},
    );
    return [response.data!];
  }

  Future<Map<String, dynamic>> getIrrigationIntelligence(String parcelId, {int windowDays = 7}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/parcels/$parcelId/irrigation/intelligence',
      queryParameters: {'window_days': windowDays},
    );
    return response.data!;
  }

  Future<Map<String, dynamic>> createCampaignResult({
    required String campaignId,
    required DateTime harvestedAt,
    required double harvestedQuantityKg,
    required double productiveAreaHa,
    double? marketableQuantityKg,
    String? qualityGrade,
    String? destination,
    String? notes,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/campaigns/$campaignId/results',
      data: {
        'campaign_id': campaignId,
        'harvested_at': harvestedAt.toUtc().toIso8601String(),
        'harvested_quantity_kg': harvestedQuantityKg,
        'productive_area_ha': productiveAreaHa,
        'marketable_quantity_kg': marketableQuantityKg,
        'quality_grade': qualityGrade,
        'destination': destination,
        'notes': notes,
      },
    );
    return response.data!;
  }

  Future<Map<String, dynamic>> getFarmCenter() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/v1/farm/center');
    return response.data!;
  }

  Future<List<Map<String, dynamic>>> getCampaigns(String parcelId) async {
    final response = await _dio.get<List<dynamic>>('/api/v1/parcels/$parcelId/campaigns');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> createCampaign({
    required String parcelId,
    required String cropType,
    required String seasonLabel,
    required DateTime startedAt,
    String? variety,
    double? targetYieldTHa,
    String? notes,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/parcels/$parcelId/campaigns',
      data: {
        'parcel_id': parcelId,
        'crop_type': cropType,
        'season_label': seasonLabel,
        'started_at': startedAt.toUtc().toIso8601String(),
        'variety': variety,
        'target_yield_t_ha': targetYieldTHa,
        'notes': notes,
      },
    );
    return response.data!;
  }

  Future<Map<String, dynamic>> getCampaignSummary(String campaignId) async {
    final response = await _dio.get<Map<String, dynamic>>('/api/v1/campaigns/$campaignId/summary');
    return response.data!;
  }

  Future<void> updateCampaignStatus({
    required String campaignId,
    required String status,
    DateTime? endedAt,
  }) async {
    await _dio.patch(
      '/api/v1/campaigns/$campaignId/status',
      data: {
        'status': status,
        'ended_at': endedAt?.toUtc().toIso8601String(),
      },
    );
  }

  Future<Map<String, dynamic>> getCampaignResultsSummary(String campaignId) async {
    final response = await _dio.get<Map<String, dynamic>>('/api/v1/campaigns/$campaignId/results/summary');
    return response.data!;
  }

  Future<List<Map<String, dynamic>>> getCampaignDecisions(String campaignId) async {
    final response = await _dio.get<List<dynamic>>('/api/v1/campaigns/$campaignId/decisions');
    return response.data!.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getIntegrationsHealth() async {
    final response = await _dio.get<Map<String, dynamic>>('/health/integrations');
    return response.data!;
  }
}
