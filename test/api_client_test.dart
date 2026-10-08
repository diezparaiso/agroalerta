import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/core/network/api_client.dart';

/// Sin Firebase configurado, `FirebaseAuth.instance` lanza excepción. El
/// cliente debe enviar la petición igualmente (sin cabecera Authorization)
/// para que el backend decida: anónimo en desarrollo, 401 en producción.
void main() {
  late HttpServer server;

  tearDown(() async {
    await server.close(force: true);
  });

  test('envia peticiones sin Firebase configurado ni cabecera Authorization', () async {
    String? authHeader;
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      authHeader = request.headers.value('Authorization');
      request.response
        ..statusCode = 200
        ..headers.contentType = ContentType.json
        ..write('[]');
      await request.response.close();
    });

    final client = ApiClient(baseUrl: 'http://127.0.0.1:${server.port}');
    final parcels = await client.getParcels();

    expect(parcels, isEmpty);
    expect(authHeader, isNull);
  });

  test('propaga el error de contrato cuando el backend responde 404', () async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) async {
      request.response
        ..statusCode = 404
        ..headers.contentType = ContentType.json
        ..write('{"detail":"Parcela no encontrada"}');
      await request.response.close();
    });

    final client = ApiClient(baseUrl: 'http://127.0.0.1:${server.port}');

    await expectLater(
      client.getParcels(),
      throwsA(isA<DioException>().having((e) => e.response?.statusCode, 'statusCode', 404)),
    );
  });
}
