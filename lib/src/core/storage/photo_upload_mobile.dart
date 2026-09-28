import 'dart:io';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';

Future<String?> uploadPhoto(String path) async {
  final user = FirebaseAuth.instance.currentUser;
  if (user == null) return null;
  final fileName = '${DateTime.now().millisecondsSinceEpoch}.jpg';
  final reference = FirebaseStorage.instance.ref('field-reports/${user.uid}/$fileName');
  await reference.putFile(File(path), SettableMetadata(contentType: 'image/jpeg'));
  return reference.getDownloadURL();
}
