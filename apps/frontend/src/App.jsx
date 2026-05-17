import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Books from './pages/Books'
import Inventory from './pages/Inventory'
import Orders from './pages/Orders'
import Login from './pages/Login'
import Register from './pages/Register'

export default function App(){
  return (
    <Router>
      <div style={{fontFamily: 'Arial, sans-serif'}}>
        <nav style={{
          backgroundColor: '#2c3e50',
          color: 'white',
          padding: '15px 20px',
          marginBottom: 20
        }}>
          <h1 style={{margin: 0, marginBottom: 10}}>📖 Prodavnica knjiga</h1>
          <ul style={{listStyle: 'none', padding: 0, margin: 0, display: 'flex', gap: 20}}>
            <li><Link to="/" style={{color: 'white', textDecoration: 'none', fontSize: 16}}>🏠 Naslovna</Link></li>
            <li><Link to="/books" style={{color: 'white', textDecoration: 'none', fontSize: 16}}>📚 Knjige</Link></li>
            <li><Link to="/inventory" style={{color: 'white', textDecoration: 'none', fontSize: 16}}>📦 Zalihе</Link></li>
            <li><Link to="/orders" style={{color: 'white', textDecoration: 'none', fontSize: 16}}>🛒 Narudžbine</Link></li>
            <li>
              {localStorage.getItem('token') ? (
                <a href="#" onClick={() => { localStorage.removeItem('token'); window.location.reload(); }} style={{color: 'white', textDecoration: 'none', fontSize: 16}}>🔒 Logout</a>
              ) : (
                <>
                  <Link to="/auth/login" style={{color: 'white', textDecoration: 'none', fontSize: 16}}>🔐 Login</Link>
                </>
              )}
            </li>
            {!localStorage.getItem('token') && (
              <li><Link to="/auth/register" style={{color: 'white', textDecoration: 'none', fontSize: 16}}>✍️ Register</Link></li>
            )}
          </ul>
        </nav>
        
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/books" element={<Books />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/auth/login" element={<Login />} />
          <Route path="/auth/register" element={<Register />} />
        </Routes>
      </div>
    </Router>
  )
}

function Home(){
  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif'}}>
      <header style={{display: 'flex', alignItems: 'center', gap: 20, marginBottom: 30}}>
        <div style={{fontSize: 40}}>📚</div>
        <div>
          <h1 style={{margin: 0}}>Dobrodošli na Naslovnu</h1>
          <p style={{margin: 0, color: '#666'}}>Malo mesto za velike knjige — pregledaj, naruči i prati zalihe.</p>
        </div>
      </header>

      <section style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 30}}>
        <div style={{background: '#f7f9fb', padding: 20, borderRadius: 8}}>
          <h2 style={{marginTop: 0}}>Istaknute knjige</h2>
          <p style={{color: '#555'}}>Pogledaj neke od najpopularnijih naslova koje preporučujemo.</p>
          <Link to="/books" style={{display: 'inline-block', marginTop: 10, padding: '8px 12px', background: '#3498db', color: 'white', textDecoration: 'none', borderRadius: 4}}>📚 Pogledaj knjige</Link>
        </div>

        <div style={{background: '#f7f9fb', padding: 20, borderRadius: 8}}>
          <h2 style={{marginTop: 0}}>Zalihe</h2>
          <p style={{color: '#555'}}>Proveri stanje zaliha i dostupnost pre naručivanja.</p>
          <Link to="/inventory" style={{display: 'inline-block', marginTop: 10, padding: '8px 12px', background: '#27ae60', color: 'white', textDecoration: 'none', borderRadius: 4}}>📦 Pregled zaliha</Link>
        </div>
      </section>

      <section style={{background: '#fff7ea', padding: 20, borderRadius: 8, marginBottom: 30}}>
        <h2 style={{marginTop: 0}}>Brzo naručivanje</h2>
        <p style={{color: '#555'}}>Imate nalog? Prijavi se i brzo kreiraj novu narudžbinu — pratimo stanje zaliha i obaveštavamo vas o promenama.</p>
        <Link to="/orders" style={{display: 'inline-block', marginTop: 10, padding: '8px 12px', background: '#e67e22', color: 'white', textDecoration: 'none', borderRadius: 4}}>🛒 Kreiraj narudžbinu</Link>
      </section>

      <footer style={{color: '#888', fontSize: 14}}>
        <p style={{margin: 0}}>Kontakt: <a href="mailto:support@example.com">support@example.com</a></p>
        <p style={{margin: '6px 0 0'}}>© {new Date().getFullYear()} Mala knjizara</p>
      </footer>
    </div>
  )
}
