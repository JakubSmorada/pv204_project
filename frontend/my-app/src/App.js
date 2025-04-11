// src/App.js
import React from 'react';
import './App.css';
import Register from './components/Register';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>User Registration with PoW</h1>
        <Register />
      </header>
    </div>
  );
}

export default App;