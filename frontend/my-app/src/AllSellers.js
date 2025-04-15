import React, { useEffect, useState } from 'react';

const AllSellers = () => {
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all sellers on component mount
  useEffect(() => {
    const fetchSellers = async () => {
      try {
        const response = await fetch('http://localhost:8000/users');
        if (!response.ok) {
          throw new Error("Error fetching sellers");
        }
        const data = await response.json();
        setSellers(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchSellers();
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h2>All Sellers</h2>
      {loading && <p>Loading sellers...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        {sellers.map((seller) => (
          <div
            key={seller.id}
            style={{
              border: '1px solid #ccc',
              borderRadius: '8px',
              padding: '16px',
              width: '600px',
              boxShadow: '2px 2px 5px rgba(0,0,0,0.1)'
            }}
          >
            <p><strong>ID:</strong> {seller.id}</p>
            <p><strong>Public Key:</strong> {seller.nostr_public_key}</p>
            <p><strong>Display Name:</strong> {seller.display_name || 'N/A'}</p>
            <p><strong>Username:</strong> {seller.username || 'N/A'}</p>
            <p><strong>About:</strong> {seller.about || 'N/A'}</p>
            <p><strong>Created At:</strong> {new Date(seller.created_at).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AllSellers;