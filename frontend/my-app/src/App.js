import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import ProtectedRoute from './ProtectedRoute';
import NostrAuth from './NostrAuth';
import HomePage from './Home';
import AllListings from './AllListings';
import AllSellers from './AllSellers';
import MyListings from './MyListings';
import CreateListing from './CreateListing';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/auth" element={<NostrAuth />} />
          <Route path="/home" element={<ProtectedRoute element={<HomePage />} />} />
          <Route path="/listings/create" element={<ProtectedRoute element={<CreateListing />} />} />
          <Route path="/listings/all" element={<ProtectedRoute element={<AllListings />} />} />
          <Route path="/listings/mine" element={<ProtectedRoute element={<MyListings />} />} />
          <Route path="/sellers/all" element={<ProtectedRoute element={<AllSellers />} />} />
          <Route path="/" element={<Navigate to="/home" />} />
          <Route path="*" element={<Navigate to="/home" />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
