import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'auth_service.dart';
import 'login_screen.dart';
import 'onboarding_screen.dart';
import 'profile_store.dart';

class AuthGate extends StatefulWidget {
  const AuthGate({required this.firebaseAvailable, required this.child, super.key});
  final bool firebaseAvailable;
  final Widget child;

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  @override
  Widget build(BuildContext context) {
    if (!widget.firebaseAvailable) return LoginScreen(authService: null, firebaseAvailable: false);
    final service = AuthService();
    return StreamBuilder<User?>(stream: service.authStateChanges, builder: (context, snapshot) {
      if (snapshot.connectionState == ConnectionState.waiting) return const Scaffold(body: Center(child: CircularProgressIndicator()));
      final user = snapshot.data;
      if (user == null) return LoginScreen(authService: service, firebaseAvailable: true);
      return FutureBuilder<bool>(future: ProfileStore().isComplete(user.uid), builder: (context, profile) {
        if (!profile.hasData) return const Scaffold(body: Center(child: CircularProgressIndicator()));
        return profile.data == true ? widget.child : OnboardingScreen(userId: user.uid, onComplete: () => setState(() {}));
      });
    });
  }
}
