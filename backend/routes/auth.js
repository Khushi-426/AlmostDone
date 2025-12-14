// backend/routes/auth.js

const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const User = require('../models/User');
const auth = require('../middleware/auth'); // <--- ADDED THIS IMPORT

// helper to create JWT
const createToken = (user) => {
  const payload = {
    user: {
      id: user.id,
      role: user.role
    }
  };

  return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: '5h' });
};

// ---------------------- GET LOGGED IN USER ----------------------
// GET /api/auth/user
// This route is called by the frontend to identify the user from the token
router.get('/user', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('-password');
    res.json(user);
  } catch (err) {
    console.error(err.message);
    res.status(500).send('Server Error');
  }
});

// ---------------------- THERAPIST REGISTER ----------------------
// POST /api/auth/therapist/register
router.post('/therapist/register', async (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ message: 'Please enter all fields.' });
  }

  try {
    let existing = await User.findOne({ email });
    if (existing) {
      return res.status(400).json({ message: 'User already exists.' });
    }

    const user = new User({
      email,
      password,
      role: 'THERAPIST'
    });

    await user.save();

    return res.status(201).json({ message: 'Therapist registered successfully.' });
  } catch (err) {
    console.error('Therapist Registration Error:', err);
    return res.status(500).json({ message: 'Server error during therapist registration.' });
  }
});

// ---------------------- PATIENT REGISTER ------------------------
// POST /api/auth/patient/register
router.post('/patient/register', async (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ message: 'Please enter all fields.' });
  }

  try {
    let existing = await User.findOne({ email });
    if (existing) {
      return res.status(400).json({ message: 'User already exists.' });
    }

    const user = new User({
      email,
      password,
      role: 'PATIENT'
    });

    await user.save();

    return res.status(201).json({ message: 'Patient registered successfully.' });
  } catch (err) {
    console.error('Patient Registration Error:', err);
    return res.status(500).json({ message: 'Server error during patient registration.' });
  }
});

// ---------------------- THERAPIST LOGIN -------------------------
// POST /api/auth/therapist/login
router.post('/therapist/login', async (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ message: 'Please enter all fields.' });
  }

  try {
    const user = await User.findOne({ email });

    if (!user) {
      return res.status(400).json({ message: 'Invalid credentials.' });
    }

    if (user.role !== 'THERAPIST') {
      return res.status(403).json({ message: 'Access denied: not a therapist account.' });
    }

    const isMatch = await user.comparePassword(password);
    if (!isMatch) {
      return res.status(400).json({ message: 'Invalid credentials.' });
    }

    const token = createToken(user);
    return res.json({ token });
  } catch (err) {
    console.error('Therapist Login Error:', err);
    return res.status(500).json({ message: 'Server error during therapist login.' });
  }
});

module.exports = router;