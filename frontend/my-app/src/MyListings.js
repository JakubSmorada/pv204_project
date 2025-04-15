import React, { useEffect, useState, useContext } from 'react';
import { AuthContext } from './AuthContext';

const MyListings = () => {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedListing, setSelectedListing] = useState(null);

  // Get current user's public key from AuthContext
  const { userPublicKey } = useContext(AuthContext);

  // Fetch listings for the logged-in user using the endpoint that returns only their listings.
  useEffect(() => {
    if (!userPublicKey) {
      setError('No public key available.');
      setLoading(false);
      return;
    }
    
    const fetchMyListings = async () => {
      try {
        // Adjust the endpoint as needed; here we assume /listings/{public_key} returns the user's listings.
        const response = await fetch(`http://localhost:8000/listings/${encodeURIComponent(userPublicKey)}`);
        if (!response.ok) {
          throw new Error('Error fetching listings');
        }
        const data = await response.json();
        setListings(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchMyListings();
  }, [userPublicKey]);

  // Open modal with detailed listing info
  const openModal = (listing) => {
    setSelectedListing(listing);
  };

  // Close modal
  const closeModal = () => {
    setSelectedListing(null);
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>My Listings</h2>
      {loading && <p>Loading your listings...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {(!loading && listings.length === 0) && <p>No listings found for you.</p>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        {listings.map((listing) => (
          <div
            key={listing.id}
            onClick={() => openModal(listing)}
            style={{
              border: '1px solid #ccc',
              borderRadius: '8px',
              padding: '16px',
              width: '300px',
              cursor: 'pointer',
              boxShadow: '2px 2px 5px rgba(0,0,0,0.1)',
              background: listing.status === "ended" ? "#ffd6d6" : "#fff"
            }}
          >
            {listing.image && listing.image.url && (
              <img
                src={listing.image.url}
                alt="Listing"
                style={{ width: '100%', borderRadius: '4px', marginBottom: '8px' }}
              />
            )}
            <h3>{listing.title}</h3>
            <p style={{ fontWeight: 'bold' }}>${listing.price}</p>
            <p>{(listing.description || "").substring(0, 100)}...</p>
          </div>
        ))}
      </div>

      {/* Modal for showing listing details */}
      {selectedListing && (
        <div
          onClick={closeModal}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#fff',
              padding: '20px',
              borderRadius: '8px',
              width: '80%',
              maxHeight: '90%',
              overflowY: 'auto',
              position: 'relative'
            }}
          >
            <button
              onClick={closeModal}
              style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                background: 'transparent',
                border: 'none',
                fontSize: '24px',
                cursor: 'pointer'
              }}
            >
              &times;
            </button>
            {selectedListing.image && selectedListing.image.url && (
              <img
                src={selectedListing.image.url}
                alt="Listing"
                style={{ width: '100%', borderRadius: '4px', marginBottom: '16px' }}
              />
            )}
            <h2>{selectedListing.title}</h2>
            <p><strong>Price:</strong> {selectedListing.price} SATs</p>
            <p><strong>Description:</strong> {selectedListing.description}</p>
            <p><strong>Condition:</strong> {selectedListing.condition}</p>
            {/* If the listing is ended, display paid_by information */}
            {selectedListing.status === "ended" && selectedListing.paid_by && (
              <p style={{ color: "green" }}>
                <strong>Paid by:</strong> {selectedListing.paid_by}
              </p>
            )}
            {/* Only show the pay button if the listing status is not ended */}
            {selectedListing.status !== "ended" && (
              <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'center' }}>
                <button onClick={() => {
                  // You could navigate to a payment flow here or open another modal
                  // For now, we simply alert:
                  alert(`Payment functionality here for listing: ${selectedListing.title}`);
                }}>
                  Pay
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MyListings;
