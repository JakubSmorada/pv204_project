// src/components/Register.js
import React, { useState } from 'react';
import api from '../services/api';

function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const calculateProofOfWork = async (challenge, difficulty) => {
    // Create the data object without hash initially
    const userData = {
      nonce: "0", // Start with nonce = 0
      challenge: challenge,
    };
    
    let nonce = 0;
    let hash = "";
    let verifyData;
    let target = '0'.repeat(difficulty);
    
    // Calculate hash until we find one with the required number of leading zeros
    while (true) {
      // Update nonce for this attempt
      userData.nonce = nonce.toString();
      
      // Create a copy without hash field for verification
      verifyData = {...userData};
      if (verifyData.hash) delete verifyData.hash;
      
      // Generate hash using SHA-256
      const dataString = `${challenge}${nonce}`
      hash = await crypto.subtle.digest(
        'SHA-256', 
        new TextEncoder().encode(dataString)
      ).then(hashBuffer => {
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      });
      
      // Check if hash meets difficulty requirements
      if (hash.startsWith(target)) {
        break;
      }
      
      nonce++;
    }
    
    return {
      nonce: nonce.toString(),
      hash: hash
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    
    try {
      // Step 1: Get the challenge from the server
      const challengeResponse = await api.getChallenge();
      const { challenge, difficulty, token } = challengeResponse.data;
      
      // Step 2: Calculate proof of work
      const pow = await calculateProofOfWork(challenge, difficulty);
      
      // Step 3: Submit registration with proof of work
      const userData = {
        username: username,
        password: password,
        nonce: pow.nonce,
        hash: pow.hash,
        active: false
      };
      
      const response = await api.registerUser(userData, token);
      setResult({ success: true, message: "Registration successful!" });
    } catch (error) {
      console.error("Registration error:", error);
      setResult({ 
        success: false, 
        message: error.response?.data?.detail || "Registration failed. Please try again." 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-container">
      <h2>Register</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Processing...' : 'Register'}
        </button>
      </form>
      
      {result && (
        <div className={`result ${result.success ? 'success' : 'error'}`}>
          {result.message}
        </div>
      )}
    </div>
  );
}

export default Register;