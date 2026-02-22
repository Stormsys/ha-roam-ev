const https = require('https');

const CONFIG = {
  firebaseApiKey: 'AIzaSyD4j5oEpmxNpjc5_sdObpQF0Pf2sk0b0LA',
  firestoreProjectId: 'prod-evc-app',
  apiBaseUrl: 'europe-west2-prod-evc-app.cloudfunctions.net',
  email: 'YOUR_EMAIL_HERE',
  password: 'YOUR_PASSWORD_HERE'
};

async function firebaseLogin(email, password) {
  console.log('🔐 Logging in to Firebase...');
  const postData = JSON.stringify({ email, password, returnSecureToken: true });

  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'identitytoolkit.googleapis.com',
      path: `/v1/accounts:signInWithPassword?key=${CONFIG.firebaseApiKey}`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          const response = JSON.parse(data);
          console.log('✅ Login successful! User ID:', response.localId);
          resolve(response);
        } else {
          reject(new Error(data));
        }
      });
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function getUserFromFirestore(idToken, userId) {
  console.log('\n👤 Getting user document from Firestore...');
  
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'firestore.googleapis.com',
      path: `/v1/projects/${CONFIG.firestoreProjectId}/databases/(default)/documents/users/${userId}`,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json'
      }
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          const doc = JSON.parse(data);
          console.log('✅ User document retrieved!');
          
          const fields = doc.fields || {};
          const getValue = (field) => {
            if (!field) return null;
            if (field.stringValue) return field.stringValue;
            if (field.integerValue) return parseInt(field.integerValue);
            if (field.doubleValue) return field.doubleValue;
            if (field.booleanValue !== undefined) return field.booleanValue;
            if (field.timestampValue) return field.timestampValue;
            if (field.mapValue) return field.mapValue.fields;
            if (field.nullValue !== undefined) return null;
            return null;
          };
          
          const currentSession = getValue(fields.currentSession);
          
          // Parse session fields if they exist
          let sessionData = null;
          if (currentSession) {
            sessionData = {
              chargerId: getValue(currentSession.chargerId),
              evseId: getValue(currentSession.evseId),
              transactionId: getValue(currentSession.transactionId),
              status: getValue(currentSession.status),
              startedChargingAt: getValue(currentSession.startedChargingAt),
              qrCode: getValue(currentSession.qrCode),
              manualInputCode: getValue(currentSession.manualInputCode),
              rateApplied: getValue(currentSession.rateApplied),
              updatedAt: getValue(currentSession.updatedAt)
            };
          }
          
          resolve({
            currentSession: sessionData,
            currentSessionEnergy: getValue(fields.currentSessionEnergy),
            transactionId: getValue(fields.transactionId),
            startedChargingAt: getValue(fields.startedChargingAt),
            firstLogin: getValue(fields.firstLogin),
            email: getValue(fields.email)
          });
        } else {
          resolve({ statusCode: res.statusCode, error: data });
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function getChargerDetails(idToken, chargerId) {
  console.log('\n🔋 Getting charger details...');
  console.log('   Charger ID:', chargerId);

  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: CONFIG.apiBaseUrl,
      path: `/evc_charge/charger/${chargerId}`,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json'
      }
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          try {
            console.log('✅ Charger data retrieved!');
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ raw: data });
          }
        } else {
          console.log('⚠️  Failed to get charger:', data);
          resolve({ statusCode: res.statusCode, error: data });
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function refreshToken(refreshToken) {
  console.log('\n🔄 Refreshing token...');
  const postData = JSON.stringify({
    grant_type: 'refresh_token',
    refresh_token: refreshToken
  });

  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'securetoken.googleapis.com',
      path: `/v1/token?key=${CONFIG.firebaseApiKey}`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        if (res.statusCode === 200) {
          const response = JSON.parse(data);
          console.log('✅ Token refreshed! Expires in:', response.expires_in, 'seconds');
          resolve(response);
        } else {
          reject(new Error(data));
        }
      });
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// Check if session is actually active
function isSessionActive(sessionData) {
  if (!sessionData) return false;
  
  // Session is active if:
  // - status > 0 (non-zero status)
  // - OR has a chargerId/evseId
  // - OR has a transactionId
  return (
    (sessionData.status && sessionData.status > 0) ||
    sessionData.chargerId ||
    sessionData.evseId ||
    sessionData.transactionId
  );
}

async function main() {
  try {
    console.log('='.repeat(60));
    console.log('EV CHARGING API - COMPLETE FLOW');
    console.log('='.repeat(60));

    // 1. LOGIN
    const loginResult = await firebaseLogin(CONFIG.email, CONFIG.password);
    const idToken = loginResult.idToken;
    const userId = loginResult.localId;
    const refreshTokenValue = loginResult.refreshToken;

    // 2. GET USER DOCUMENT
    const userData = await getUserFromFirestore(idToken, userId);
    
    console.log('\n📊 User Info:');
    console.log('   Email:', userData.email);
    console.log('   First Login:', userData.firstLogin);

    // 3. CHECK FOR ACTIVE SESSION
    if (isSessionActive(userData.currentSession)) {
      console.log('\n⚡ ACTIVE CHARGING SESSION!');
      console.log('   Status:', userData.currentSession.status);
      console.log('   Charger ID:', userData.currentSession.chargerId);
      console.log('   EVSE ID:', userData.currentSession.evseId);
      console.log('   Transaction ID:', userData.currentSession.transactionId);
      console.log('   Started At:', userData.currentSession.startedChargingAt);
      
      // Get energy info
      if (userData.currentSessionEnergy) {
        const energy = userData.currentSessionEnergy;
        console.log('\n📊 Current Energy:');
        console.log('   Power:', energy.power?.integerValue || 0, 'W');
        console.log('   Energy:', energy.energy?.integerValue || 0, 'Wh');
        console.log('   Updated At:', energy.updatedAt?.timestampValue);
      }
      
      // 4. GET DETAILED CHARGER INFO
      if (userData.currentSession.chargerId || userData.currentSession.evseId) {
        const chargerId = userData.currentSession.chargerId || userData.currentSession.evseId;
        const chargerData = await getChargerDetails(idToken, chargerId);
        console.log('\n🔌 Charger Details:');
        console.log(JSON.stringify(chargerData, null, 2));
      }
      
    } else {
      console.log('\n✅ No active charging session.');
      console.log('   Status: Idle (status = 0)');
      
      if (userData.currentSessionEnergy) {
        console.log('\n   Last session info:');
        console.log('   - Last updated:', userData.currentSessionEnergy.updatedAt?.timestampValue);
      }
    }

    // 5. DEMONSTRATE TOKEN REFRESH
    const newTokenData = await refreshToken(refreshTokenValue);

    console.log('\n' + '='.repeat(60));
    console.log('✅ COMPLETE! All flows working.');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  }
}

if (require.main === module) {
  main();
}

module.exports = { 
  firebaseLogin, 
  getUserFromFirestore, 
  getChargerDetails, 
  refreshToken,
  isSessionActive
};
