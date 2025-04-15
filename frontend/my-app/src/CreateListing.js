import React, { useState } from 'react';

/**
 * Computes a proof-of-work nonce.
 * It serializes the data (with sorted keys), concatenates it with the nonce,
 * computes the SHA-256 hash, and checks whether it starts with the required number of zeros.
 *
 * @param {Object} data - The listing data (without nonce)
 * @param {number} difficulty - Number of leading zeros required (default 4)
 * @returns {Promise<{ nonce: number, hash: string }>}
 */
async function computeProofOfWork(data, difficulty = 7) {
    let nonce = 0;
    const encoder = new TextEncoder();
    const requiredPrefix = "0".repeat(difficulty);
    
    // Create a copy of data without the "nonce" field
    const dataToHash = { ...data };
    delete dataToHash.nonce;
    
    // Sort keys to enforce ordering
    const sortedKeys = Object.keys(dataToHash).sort();
    // Serialize the data using sorted keys (JSON.stringify produces a compact string)
    const baseStr = JSON.stringify(dataToHash, sortedKeys);
    
    while (true) {
      const combined = baseStr + nonce;
      const hashBuffer = await crypto.subtle.digest("SHA-256", encoder.encode(combined));
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join('');
      if (hashHex.startsWith(requiredPrefix)) {
        return { nonce, hash: hashHex };
      }
      nonce++;
    }
  }

const CreateListing = () => {
  // State for listing fields
  const [title, setTitle] = useState('Example Listing Title');
  const [description, setDescription] = useState(
    'This is an example description that meets the minimum requirement. Feel free to change it as needed.'
  );
  const [condition, setCondition] = useState('new');
  const [price, setPrice] = useState(10); // Price as integer
  const [image, setImage] = useState('https://example.com/image1.jpg');

  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Retrieve the user’s token from localStorage (or your AuthContext)
  const token = localStorage.getItem('authToken') || '';
  const pubkey = localStorage.getItem('userPublicKey');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('Computing proof-of-work (this may take a moment)...');

    // Prepare the base payload without nonce.
    const basePayload = {
      title,
      description,
      condition,
      price: Number(price),                  
      image,
      pubkey
    };

    try {
      // Compute a valid nonce that makes the hash start with "0000"
      const { nonce, hash } = await computeProofOfWork(basePayload, 4);
      setMessage(`Proof-of-work successful! Nonce: ${nonce} - Hash: ${hash}`);
      
      // Append the nonce to the payload
      const payload = {
        ...basePayload,
        nonce,
      };

      // Build the request URL with the token as a query parameter
      const url = `http://localhost:8000/listings?session-token=${encodeURIComponent(token)}`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to create listing');
      }

      const responseData = await response.json();
      setMessage('Listing created successfully!');
      console.log('Server response:', responseData);
      // Optionally, reset form fields here.
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ margin: '20px' }}>
      <h2>Create a Listing</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '10px' }}>
          <label>
            Title:&nbsp;
            <input 
              type="text" 
              value={title} 
              onChange={(e) => setTitle(e.target.value)} 
              required 
            />
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            Description:&nbsp;
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={4}
              cols={50}
            />
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            Condition:&nbsp;
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              required
            >
              <option value="new">New</option>
              <option value="like_new">Like New</option>
              <option value="very_good">Very Good</option>
              <option value="good">Good</option>
              <option value="acceptable">Acceptable</option>
              <option value="for_parts">For Parts</option>
            </select>
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            Price:&nbsp;
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              required
            />
          </label>
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>
            Images (comma separated URLs):&nbsp;
            <input
              type="text"
              value={image}
              onChange={(e) => setImage(e.target.value)}
              required
            />
          </label>
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Processing...' : 'Create Listing'}
        </button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
};

export default CreateListing;
