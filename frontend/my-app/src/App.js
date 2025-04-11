import React, { useState, useEffect } from 'react';
import Register from './components/Register';
import Login from './components/Login';
import api from './services/api';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('authToken');
      if (token) {
        try {
          const response = await api.getCurrentUser();
          setUserData(response.data);
          setIsLoggedIn(true);
        } catch (error) {
          localStorage.removeItem('authToken');
        }
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  const handleLogin = async () => {
    try {
      const response = await api.getCurrentUser();
      setUserData(response.data);
      setIsLoggedIn(true);
    } catch (error) {
      console.error("Error fetching user data after login:", error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setIsLoggedIn(false);
    setUserData(null);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (isLoggedIn) {
    return (
      <div>
        <h1>Welcome {userData ? userData.username : 'User'}!</h1>
        <p>You are logged in successfully.</p>
        <button onClick={handleLogout}>Logout</button>
      </div>
    );
  }

  return (
    <div>
      <h1>Authentication Demo</h1>
      
      {showRegister ? (
        <>
          <Register />
          <p>
            Already have an account?{' '}
            <button onClick={() => setShowRegister(false)}>
              Login
            </button>
          </p>
        </>
      ) : (
        <>
          <Login onLoginSuccess={handleLogin} />
          <p>
            Don't have an account?{' '}
            <button onClick={() => setShowRegister(true)}>
              Register
            </button>
          </p>
        </>
      )}
    </div>
  );
}

export default App;