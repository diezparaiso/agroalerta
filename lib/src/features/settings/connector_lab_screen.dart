import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:file_saver/file_saver.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/network/api_client.dart';

class ConnectorLabScreen extends StatefulWidget {
  const ConnectorLabScreen({super.key});

  @override
  State<ConnectorLabScreen> createState() => _ConnectorLabScreenState();
}

class _ConnectorLabScreenState extends State<ConnectorLabScreen> {
  final ApiClient _api = ApiClient();
  final TextEditingController _municipality = TextEditingController(text: '41091');
  final Map<String, Map<String, dynamic>> _results = {};
  String? _loading;

  static const _connectors = [
    ('ria', 'RIA-IFAPA', Icons.agriculture_outlined),
    ('aemet', 'AEMET', Icons.cloud_outlined),
    ('mapa', 'MAPA', Icons.account_balance_outlined),
    ('sigpac', 'SIGPAC', Icons.map_outlined),
  ];

  @override
  void dispose() {
    _municipality.dispose();
    super.dispose();
  }

  Future<void> _test(String id) async {
    setState(() => _loading = id);
    try {
      final response = await _api.testConnector(
        id,
        municipalityCode: _municipality.text.trim(),
      );
      if (!mounted) return;
      setState(() => _results[id] = response);
    } on DioException catch (error) {
      if (!mounted) return;
      setState(() => _results[id] = {
        'connector': id.toUpperCase(),
        'status': 'error',
        'message': error.response?.data is Map
            ? (error.response!.data as Map)['detail']?.toString()
            : error.message,
        'raw_data': error.response?.data,
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _results[id] = {
        'connector': id.toUpperCase(),
        'status': 'error',
        'message': error.toString(),
      });
    } finally {
      if (mounted) setState(() => _loading = null);
    }
  }

  Color _statusColor(String? status) => switch (status) {
        'connected' => Colors.green,
        'empty' || 'not_configured' || 'not_implemented' => Colors.orange,
        'error' || 'invalid_response' => Colors.red,
        _ => Colors.grey,
      };

  String _statusLabel(String? status) => switch (status) {
        'connected' => 'Conectado · respuesta real',
        'empty' => 'Conectado · sin registros',
        'not_configured' => 'Sin configurar',
        'not_implemented' => 'Pendiente de implementar',
        'invalid_response' => 'Respuesta inesperada',
        'error' => 'Error de conexión',
        _ => 'Sin probar',
      };

  List<MapEntry<String, dynamic>> _flatten(Map<String, dynamic> map, [String prefix = '']) {
    final rows = <MapEntry<String, dynamic>>[];
    for (final entry in map.entries) {
      final key = prefix.isEmpty ? entry.key : '$prefix.${entry.key}';
      if (entry.value is Map) {
        rows.addAll(_flatten(Map<String, dynamic>.from(entry.value as Map), key));
      } else if (entry.value is List) {
        rows.add(MapEntry(key, jsonEncode(entry.value)));
      } else {
        rows.add(MapEntry(key, entry.value));
      }
    }
    return rows;
  }

  Future<void> _export(String id) async {
    final result = _results[id];
    if (result == null) return;
    final raw = result['raw_data'];
    final records = raw is List
        ? raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList()
        : raw is Map
            ? [Map<String, dynamic>.from(raw)]
            : <Map<String, dynamic>>[];
    final keys = <String>{};
    for (final record in records) {
      keys.addAll(record.keys);
    }
    final columns = keys.toList();
    final rows = <List<String>>[
      columns,
      ...records.map((record) => columns.map((key) {
            final value = record[key];
            return value == null ? '' : value is Map || value is List ? jsonEncode(value) : value.toString();
          }).toList()),
    ];
    String csvCell(String value) => '"${value.replaceAll('"', '""')}"';
    final csv = rows.map((row) => row.map(csvCell).join(';')).join('\r\n');
    final bytes = Uint8List.fromList([0xEF, 0xBB, 0xBF, ...utf8.encode(csv)]);
    await FileSaver.instance.saveFile(
      name: 'agroalerta_${id}_${DateTime.now().toIso8601String().substring(0, 10)}',
      bytes: bytes,
      ext: 'csv',
      mimeType: MimeType.csv,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Laboratorio de conectores'),
        actions: [
          IconButton(
            tooltip: 'Copiar respuesta JSON',
            onPressed: _results.isEmpty
                ? null
                : () => Clipboard.setData(ClipboardData(text: const JsonEncoder.withIndent('  ').convert(_results))),
            icon: const Icon(Icons.copy_all_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Pruebas directas de los servicios. Solo se marcará como conectado cuando se reciba una respuesta real.',
            style: TextStyle(fontSize: 14),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _municipality,
            keyboardType: TextInputType.number,
            maxLength: 5,
            decoration: const InputDecoration(
              labelText: 'Código INE municipio para AEMET',
              helperText: 'Por defecto 41091 (Sevilla). Solo se usa en la prueba AEMET.',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          for (final connector in _connectors) _connectorCard(connector),
          if (_results.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Text('Resultados recibidos', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            for (final connector in _connectors)
              if (_results.containsKey(connector.$1)) _resultPanel(connector.$1),
          ],
        ],
      ),
    );
  }

  Widget _connectorCard((String, String, IconData) connector) {
    final result = _results[connector.$1];
    final status = result?['status']?.toString();
    return Card(
      child: ListTile(
        leading: Icon(connector.$3),
        title: Text(connector.$2),
        subtitle: Text(_statusLabel(status)),
        trailing: FilledButton.tonal(
          onPressed: _loading == null ? () => _test(connector.$1) : null,
          child: _loading == connector.$1
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Probar'),
        ),
      ),
    );
  }

  Widget _resultPanel(String id) {
    final result = _results[id]!;
    final status = result['status']?.toString();
    final raw = result['raw_data'];
    final records = raw is List
        ? raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList()
        : raw is Map
            ? [Map<String, dynamic>.from(raw)]
            : <Map<String, dynamic>>[];
    final fields = <String>{};
    for (final record in records) {
      fields.addAll(record.keys);
    }
    return Card(
      margin: const EdgeInsets.only(top: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.circle, size: 12, color: _statusColor(status)),
              const SizedBox(width: 8),
              Expanded(child: Text(_statusLabel(status), style: const TextStyle(fontWeight: FontWeight.w600))),
              IconButton(
                tooltip: 'Exportar CSV para Excel',
                onPressed: raw == null ? null : () => _export(id),
                icon: const Icon(Icons.file_download_outlined),
              ),
            ]),
            if (result['message'] != null) Text(result['message'].toString()),
            if (result['tested_at'] != null)
              Text('Consulta: ${result['tested_at']}', style: Theme.of(context).textTheme.bodySmall),
            if (result['record_count'] != null)
              Text('Registros: ${result['record_count']} · Campos: ${fields.length}'),
            if (fields.isNotEmpty) ...[
              const Divider(),
              const Text('Campos devueltos por el servicio:', style: TextStyle(fontWeight: FontWeight.bold)),
              Wrap(spacing: 6, runSpacing: 4, children: fields.map((f) => Chip(label: Text(f))).toList()),
              const SizedBox(height: 8),
              ...records.take(3).map((record) => ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: Text('Registro ${records.indexOf(record) + 1}'),
                    children: _flatten(record).map((entry) => ListTile(
                          dense: true,
                          title: Text(entry.key, style: const TextStyle(fontSize: 12)),
                          subtitle: SelectableText(entry.value?.toString() ?? 'null'),
                        )).toList(),
                  )),
              if (records.length > 3) Text('Se muestran 3 registros de ${records.length}; la exportación incluye todos.'),
            ] else if (raw != null)
              SelectableText(const JsonEncoder.withIndent('  ').convert(raw)),
          ],
        ),
      ),
    );
  }
}
