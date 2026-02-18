import { Routes, Route, NavLink } from 'react-router-dom'
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react'
import Challenges from './pages/Challenges'
import Builder from './pages/Builder'
import MyMazes from './pages/MyMazes'
import Settings from './pages/Settings'
import Leaderboard from './pages/Leaderboard'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <nav className="main-nav">
        <div className="nav-brand">
          <span className="brand-icon">◈</span>
          <span className="brand-text">Maze Architect</span>
        </div>
        
        <div className="nav-links">
          <NavLink to="/challenges">Challenges</NavLink>
          <NavLink to="/mazebench">MazeBench</NavLink>
          <NavLink to="/builder">Builder</NavLink>
          <SignedIn>
            <NavLink to="/my-mazes">My Mazes</NavLink>
          </SignedIn>
        </div>
        
        <div className="nav-auth">
          <SignedOut>
            <SignInButton mode="modal" />
          </SignedOut>
          <SignedIn>
            <NavLink to="/settings">Settings</NavLink>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </nav>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Challenges />} />
          <Route path="/challenges" element={<Challenges />} />
          <Route path="/mazebench" element={<Leaderboard />} />
          <Route path="/builder" element={<Builder />} />
          <Route path="/my-mazes" element={<MyMazes />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
