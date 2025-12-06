// TODO: Replace with real Firebase Auth initialization
// mockAuthLogin() → always returns a dummy user

function mockAuthLogin(email, password) {
  console.log("Mock auth login", { email, password });
  // Always succeed; backend will also mock-accept.
  return true;
}

