import React from 'react';
import { useNavigate } from 'react-router-dom';

const HomePage = () => {
  const navigate = useNavigate();

  const handleCreateListing = () => navigate('/listings/create');
  const handleMyListings = () => navigate('/listings/mine');
  const handleAllListings = () => navigate('/listings/all');
  const handleAllSellers = () => navigate('/sellers/all');

  return (
    <div style={{ margin: '20px' }}>
      <h2>Welcome Home</h2>
      <p>Choose an action:</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '200px' }}>
        <button onClick={handleCreateListing}>Create a Listing</button>
        <button onClick={handleMyListings}>My Listings</button>
        <button onClick={handleAllListings}>All Listings</button>
        <button onClick={handleAllSellers}>All sellers</button>
      </div>
    </div>
  );
};

export default HomePage;