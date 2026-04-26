import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
const Nav = () => {
    const auth = localStorage.getItem("user");
    const navigate = useNavigate();
    const logout = () => {
        localStorage.clear();
        navigate("/signup");
    }
    return (
        <div>
            <img alt='logo' className='logo' src="https://imgs.search.brave.com/Lki3lwylsG97P780kFc7H0oKvWmaLRxBaKblZHM9nFE/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9jZG4u/ZHJpYmJibGUuY29t/L3VzZXJ1cGxvYWQv/MTc5MDMyMTMvZmls/ZS9vcmlnaW5hbC1k/MDg1YTMwMGE5ZDE3/MmUyMjBhYmFiZDBj/NjVhZjc5OC5qcGVn/P2Zvcm1hdD13ZWJw/JnJlc2l6ZT00MDB4/MzAwJnZlcnRpY2Fs/PWNlbnRlcg"></img>
            {auth ? <ul className="nav-ul">
                <li><Link to="/">Products</Link></li>
                <li><Link to="/add">Add Products</Link></li>
                {/* <li><Link to="/update">Update Products</Link></li> */}
                <li><Link to="/profile">Profile</Link></li>
                {/* <li>{auth ? <Link onClick={logout} to="/signup">Logout</Link> : <Link to="/signup">Sign Up</Link>}</li>
                <li><Link to="/login">Login</Link></li> */}
                {auth ? <li><Link onClick={logout} to="/signup">Logout ({JSON.parse(auth).name})</Link></li>
                    : <>

                    </>
                }
            </ul> : <ul className='nav-ul nav-right'>
                <li><Link to="/signup">Sign Up</Link></li>
                <li><Link to="/login">Login</Link></li>
            </ul>}
        </div>
    );
}

export default Nav;