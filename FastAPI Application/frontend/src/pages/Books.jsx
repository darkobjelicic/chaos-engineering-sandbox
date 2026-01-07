import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function Books(){
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(()=>{
    axios.get('http://localhost:8000/books')
      .then(r=> {
        setBooks(r.data || [])
        setLoading(false)
      })
      .catch(err=> {
        console.error('Greška pri učitavanju knjiga:', err)
        setError('Nije moguće učitati knjige')
        setLoading(false)
      })
  },[])

  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif'}}>
      <h1>📚 Katalog knjiga</h1>
      {loading && <p>Učitavanje...</p>}
      {error && <p style={{color: 'red'}}>{error}</p>}
      {!loading && books.length === 0 ? (
        <p>Nema knjiga</p>
      ) : (
        <ul style={{listStyle: 'none', padding: 0}}>
          {books.map(b => (
            <li key={b.id} style={{
              padding: 15,
              margin: 10,
              border: '1px solid #ddd',
              borderRadius: 5,
              backgroundColor: '#f9f9f9'
            }}>
              <strong style={{fontSize: 16}}>{b.title}</strong> 
              <br />
              <span style={{color: '#666'}}>Autor: {b.author}</span>
              <br />
              <span style={{color: '#27ae60', fontWeight: 'bold', fontSize: 14}}>💰 {b.price} дин</span>
              {b.description && <p style={{fontSize: 12, color: '#666', marginTop: 5}}>{b.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
