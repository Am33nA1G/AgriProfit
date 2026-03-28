"""
District neighbor mapping for intelligent alert targeting.

Maps neighboring districts for Indian states so alert posts
can notify users in affected areas (same + adjacent districts).
"""


# Kerala - 14 districts fully mapped
KERALA_NEIGHBORS: dict[str, list[str]] = {
    "Thiruvananthapuram": ["Kollam", "Pathanamthitta"],
    "Kollam": ["Thiruvananthapuram", "Pathanamthitta", "Alappuzha"],
    "Pathanamthitta": ["Thiruvananthapuram", "Kollam", "Alappuzha", "Kottayam", "Idukki"],
    "Alappuzha": ["Kollam", "Pathanamthitta", "Kottayam", "Ernakulam"],
    "Kottayam": ["Pathanamthitta", "Alappuzha", "Ernakulam", "Idukki"],
    "Idukki": ["Pathanamthitta", "Kottayam", "Ernakulam", "Thrissur"],
    "Ernakulam": ["Alappuzha", "Kottayam", "Idukki", "Thrissur"],
    "Thrissur": ["Ernakulam", "Idukki", "Palakkad", "Malappuram"],
    "Palakkad": ["Thrissur", "Malappuram"],
    "Malappuram": ["Thrissur", "Palakkad", "Kozhikode", "Wayanad"],
    "Kozhikode": ["Malappuram", "Wayanad", "Kannur"],
    "Wayanad": ["Malappuram", "Kozhikode", "Kannur"],
    "Kannur": ["Kozhikode", "Wayanad", "Kasaragod"],
    "Kasaragod": ["Kannur"],
}

# Punjab - 23 districts mapped
PUNJAB_NEIGHBORS: dict[str, list[str]] = {
    "Amritsar": ["Tarn Taran", "Gurdaspur", "Kapurthala"],
    "Tarn Taran": ["Amritsar", "Kapurthala", "Ferozepur"],
    "Gurdaspur": ["Amritsar", "Pathankot", "Hoshiarpur"],
    "Pathankot": ["Gurdaspur", "Hoshiarpur"],
    "Hoshiarpur": ["Gurdaspur", "Pathankot", "Jalandhar", "Nawanshahr"],
    "Jalandhar": ["Hoshiarpur", "Kapurthala", "Nawanshahr", "Ludhiana"],
    "Kapurthala": ["Amritsar", "Tarn Taran", "Jalandhar", "Ferozepur"],
    "Nawanshahr": ["Hoshiarpur", "Jalandhar", "Ludhiana", "Rupnagar"],
    "Ludhiana": ["Jalandhar", "Nawanshahr", "Rupnagar", "Fatehgarh Sahib", "Moga", "Sangrur"],
    "Moga": ["Ludhiana", "Ferozepur", "Faridkot", "Sangrur"],
    "Ferozepur": ["Tarn Taran", "Kapurthala", "Moga", "Faridkot", "Fazilka"],
    "Fazilka": ["Ferozepur", "Faridkot", "Muktsar"],
    "Faridkot": ["Ferozepur", "Fazilka", "Moga", "Muktsar", "Bathinda"],
    "Muktsar": ["Fazilka", "Faridkot", "Bathinda"],
    "Bathinda": ["Faridkot", "Muktsar", "Mansa", "Sangrur"],
    "Mansa": ["Bathinda", "Sangrur"],
    "Sangrur": ["Ludhiana", "Moga", "Bathinda", "Mansa", "Fatehgarh Sahib", "Patiala", "Barnala"],
    "Barnala": ["Sangrur"],
    "Patiala": ["Sangrur", "Fatehgarh Sahib", "Rupnagar", "Mohali"],
    "Fatehgarh Sahib": ["Ludhiana", "Rupnagar", "Patiala", "Sangrur"],
    "Rupnagar": ["Nawanshahr", "Ludhiana", "Fatehgarh Sahib", "Mohali"],
    "Mohali": ["Rupnagar", "Patiala"],
}

# Uttar Pradesh - major districts
UP_NEIGHBORS: dict[str, list[str]] = {
    "Lucknow": ["Unnao", "Sitapur", "Hardoi", "Barabanki", "Raebareli"],
    "Agra": ["Mathura", "Firozabad", "Etah", "Mainpuri"],
    "Varanasi": ["Jaunpur", "Chandauli", "Ghazipur", "Mirzapur"],
    "Kanpur Nagar": ["Kanpur Dehat", "Unnao", "Fatehpur", "Hamirpur"],
    "Allahabad": ["Fatehpur", "Kaushambi", "Pratapgarh", "Mirzapur"],
    "Meerut": ["Ghaziabad", "Baghpat", "Bulandshahr", "Muzaffarnagar", "Hapur"],
    "Ghaziabad": ["Meerut", "Hapur", "Bulandshahr", "Gautam Buddha Nagar"],
    "Bareilly": ["Pilibhit", "Shahjahanpur", "Badaun", "Rampur"],
    "Gorakhpur": ["Deoria", "Kushinagar", "Maharajganj", "Sant Kabir Nagar"],
    "Jhansi": ["Lalitpur", "Hamirpur", "Mahoba"],
}

# Maharashtra - major districts
MAHARASHTRA_NEIGHBORS: dict[str, list[str]] = {
    "Mumbai": ["Thane", "Raigad"],
    "Pune": ["Satara", "Solapur", "Ahmednagar", "Raigad"],
    "Nagpur": ["Wardha", "Amravati", "Bhandara", "Chandrapur"],
    "Nashik": ["Dhule", "Jalgaon", "Ahmednagar", "Thane"],
    "Aurangabad": ["Jalna", "Beed", "Nashik", "Ahmednagar"],
    "Kolhapur": ["Sangli", "Satara", "Ratnagiri", "Sindhudurg"],
    "Solapur": ["Pune", "Satara", "Sangli", "Osmanabad", "Ahmednagar"],
    "Thane": ["Mumbai", "Raigad", "Nashik", "Palghar"],
    "Ahmednagar": ["Pune", "Nashik", "Aurangabad", "Solapur", "Beed"],
    "Satara": ["Pune", "Solapur", "Sangli", "Kolhapur", "Ratnagiri"],
}

# Madhya Pradesh - major districts
MP_NEIGHBORS: dict[str, list[str]] = {
    "Bhopal": ["Sehore", "Raisen", "Vidisha"],
    "Indore": ["Dewas", "Ujjain", "Dhar", "Khargone"],
    "Jabalpur": ["Narsinghpur", "Katni", "Mandla", "Seoni"],
    "Gwalior": ["Shivpuri", "Bhind", "Morena", "Datia"],
    "Ujjain": ["Indore", "Dewas", "Ratlam", "Shajapur"],
}

# Rajasthan - major districts
RAJASTHAN_NEIGHBORS: dict[str, list[str]] = {
    "Jaipur": ["Dausa", "Tonk", "Ajmer", "Sikar", "Alwar"],
    "Jodhpur": ["Nagaur", "Pali", "Barmer", "Jaisalmer"],
    "Udaipur": ["Rajsamand", "Chittorgarh", "Dungarpur", "Banswara"],
    "Kota": ["Bundi", "Baran", "Jhalawar", "Chittorgarh"],
    "Ajmer": ["Jaipur", "Tonk", "Bhilwara", "Nagaur", "Pali"],
}

# Karnataka - major districts
KARNATAKA_NEIGHBORS: dict[str, list[str]] = {
    "Bengaluru Urban": ["Bengaluru Rural", "Ramanagara", "Chikkaballapur"],
    "Mysuru": ["Mandya", "Chamarajanagar", "Kodagu", "Hassan"],
    "Hubli-Dharwad": ["Belgaum", "Gadag", "Haveri", "Uttara Kannada"],
    "Mangalore": ["Udupi", "Hassan", "Kodagu"],
    "Belgaum": ["Hubli-Dharwad", "Bagalkot", "Raichur"],
}

# Tamil Nadu - major districts
TN_NEIGHBORS: dict[str, list[str]] = {
    "Chennai": ["Tiruvallur", "Kancheepuram", "Chengalpattu"],
    "Coimbatore": ["Tirupur", "Nilgiris", "Erode"],
    "Madurai": ["Theni", "Dindigul", "Sivaganga", "Virudhunagar"],
    "Salem": ["Namakkal", "Dharmapuri", "Erode", "Villupuram"],
    "Tiruchirappalli": ["Karur", "Namakkal", "Perambalur", "Ariyalur", "Pudukkottai"],
}

# Gujarat - major districts
GUJARAT_NEIGHBORS: dict[str, list[str]] = {
    "Ahmedabad": ["Gandhinagar", "Kheda", "Mehsana", "Anand"],
    "Surat": ["Navsari", "Tapi", "Bharuch"],
    "Vadodara": ["Anand", "Kheda", "Panchmahal", "Chhota Udaipur", "Bharuch"],
    "Rajkot": ["Jamnagar", "Junagadh", "Morbi", "Surendranagar"],
}

# Haryana - all districts
HARYANA_NEIGHBORS: dict[str, list[str]] = {
    "Gurugram": ["Faridabad", "Rewari", "Nuh"],
    "Faridabad": ["Gurugram", "Palwal", "Nuh"],
    "Hisar": ["Bhiwani", "Jind", "Fatehabad", "Sirsa"],
    "Karnal": ["Panipat", "Kaithal", "Kurukshetra", "Jind"],
    "Panipat": ["Karnal", "Jind", "Sonipat"],
    "Ambala": ["Kurukshetra", "Yamunanagar", "Panchkula"],
    "Rohtak": ["Sonipat", "Jhajjar", "Bhiwani", "Jind"],
    "Sonipat": ["Panipat", "Rohtak", "Jhajjar", "Jind"],
}

# Andhra Pradesh - major districts
AP_NEIGHBORS: dict[str, list[str]] = {
    "Visakhapatnam": ["Vizianagaram", "East Godavari"],
    "Vijayawada": ["Guntur", "Krishna", "West Godavari"],
    "Guntur": ["Vijayawada", "Prakasam", "Krishna"],
    "Tirupati": ["Chittoor", "Nellore", "Kadapa"],
    "Kurnool": ["Anantapur", "Kadapa", "Prakasam"],
}

# West Bengal - major districts
WB_NEIGHBORS: dict[str, list[str]] = {
    "Kolkata": ["North 24 Parganas", "South 24 Parganas", "Howrah"],
    "Howrah": ["Kolkata", "Hooghly", "South 24 Parganas"],
    "Bardhaman": ["Hooghly", "Bankura", "Birbhum", "Nadia"],
    "Nadia": ["Bardhaman", "Murshidabad", "North 24 Parganas"],
}

# State -> neighbor mapping lookup
_STATE_MAPPINGS: dict[str, dict[str, list[str]]] = {
    "kerala": KERALA_NEIGHBORS,
    "punjab": PUNJAB_NEIGHBORS,
    "uttar pradesh": UP_NEIGHBORS,
    "maharashtra": MAHARASHTRA_NEIGHBORS,
    "madhya pradesh": MP_NEIGHBORS,
    "rajasthan": RAJASTHAN_NEIGHBORS,
    "karnataka": KARNATAKA_NEIGHBORS,
    "tamil nadu": TN_NEIGHBORS,
    "gujarat": GUJARAT_NEIGHBORS,
    "haryana": HARYANA_NEIGHBORS,
    "andhra pradesh": AP_NEIGHBORS,
    "west bengal": WB_NEIGHBORS,
}


def get_neighboring_districts(district: str, state: str) -> list[str]:
    """
    Get list of neighboring districts for a given district in a state.

    Args:
        district: District name (case-insensitive matching attempted)
        state: State name

    Returns:
        List of neighboring district names (may be empty if state/district not mapped)
    """
    mapping = _STATE_MAPPINGS.get(state.lower().strip(), {})
    if not mapping:
        return []

    # Try exact match first
    neighbors = mapping.get(district, None)
    if neighbors is not None:
        return neighbors

    # Try case-insensitive match
    district_lower = district.lower().strip()
    for key, value in mapping.items():
        if key.lower() == district_lower:
            return value

    return []


def get_target_districts(district: str, state: str) -> list[str]:
    """
    Get the user's own district + neighboring districts.

    Args:
        district: User's district
        state: User's state

    Returns:
        List including the district itself + all neighbors
    """
    neighbors = get_neighboring_districts(district, state)
    return [district] + neighbors
