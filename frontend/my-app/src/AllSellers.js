import React, { useEffect, useState } from 'react';

const AllSellers = () => {
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSeller, setSelectedSeller] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [showModal, setShowModal] = useState(false);

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

  const handleShowReviews = async (sellerPubKey) => {
    try {
      const response = await fetch(`http://localhost:8000/reviews/seller/${sellerPubKey}`);
      if (!response.ok) {
        throw new Error("Error fetching reviews");
      }
      const data = await response.json();
      setReviews(data);
      setSelectedSeller(sellerPubKey);
      setShowModal(true);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setReviews([]);
    setSelectedSeller(null);
  };

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
            <button
              style={{
                marginTop: '10px',
                padding: '8px 16px',
                backgroundColor: '#007BFF',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
              onClick={() => handleShowReviews(seller.nostr_public_key)}
            >
              Reviews
            </button>
          </div>
        ))}
      </div>

      {showModal && (
        <div
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: '#fff',
            padding: '20px',
            borderRadius: '8px',
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
            zIndex: 1000
          }}
        >
          <h3>Reviews for Seller {selectedSeller}</h3>
          {reviews.length > 0 ? (
            <ul>
              {reviews.map((review, index) => (
                <li key={index}>{review}</li>
              ))}
            </ul>
          ) : (
            <p>No reviews available.</p>
          )}
          <button
            style={{
              marginTop: '10px',
              padding: '8px 16px',
              backgroundColor: '#FF0000',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
            onClick={handleCloseModal}
          >
            Close
          </button>
        </div>
      )}

      {showModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 999
          }}
          onClick={handleCloseModal}
        />
      )}
    </div>
  );
};

export default AllSellers;