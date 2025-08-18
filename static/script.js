document.addEventListener('DOMContentLoaded', () => {
    // Set default dates
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const searchBtn = document.getElementById('search-btn');

    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const thirtyDaysFromNow = new Date(today);
    thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);

    startDateInput.value = tomorrow.toISOString().split('T')[0];
    endDateInput.value = thirtyDaysFromNow.toISOString().split('T')[0];

    // Initial fetch and event listener for the button
    fetchCheapestFlights();
    searchBtn.addEventListener('click', fetchCheapestFlights);
    
    handleSubscriptionForm();
});

async function fetchCheapestFlights() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    if (!startDate || !endDate) {
        alert("Please select a start and end date.");
        return;
    }

    const cardBodies = document.querySelectorAll('.card-body');

    // Show loading overlays
    cardBodies.forEach(body => body.classList.add('loading'));

    try {
        const response = await fetch(`/api/cheapest-flights?startDate=${startDate}&endDate=${endDate}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const flights = await response.json();
        
        updateFlightCard('SIN', flights.SIN);
        updateFlightCard('MNL', flights.MNL);

    } catch (error) {
        console.error("Failed to fetch flight data:", error);
    } finally {
        // Hide loading overlays
        cardBodies.forEach(body => body.classList.remove('loading'));
    }
}

function updateFlightCard(destinationCode, flightData) {
    const card = document.getElementById(`deal-${destinationCode}`);

    // --- Helper Functions ---
    const formatPrice = (price) => {
        if (price === null || price === undefined) return 'N/A';
        return new Intl.NumberFormat('ja-JP', { 
            style: 'currency', currency: 'JPY', minimumFractionDigits: 0, maximumFractionDigits: 0 
        }).format(price);
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC'
        });
    };

    const formatFlightInfo = (flight) => {
        if (!flight || !flight.date) return 'No flights found';
        let datePart = formatDate(flight.date);
        let timePart = '';
        // Check specifically for departure_time and arrival_time
        if (flight.departure_time && flight.arrival_time) {
            timePart = ` (${flight.departure_time} → ${flight.arrival_time})`;
        }
        return datePart + timePart;
    };

    // --- Update UI Elements ---
    const outboundOneway = flightData.oneWay;
    card.querySelector('.outbound-oneway-price').textContent = formatPrice(outboundOneway?.price);
    card.querySelector('.outbound-oneway-info').textContent = formatFlightInfo(outboundOneway);
    
    const returnOneway = flightData.returnOneway;
    card.querySelector('.return-oneway-price').textContent = formatPrice(returnOneway?.price);
    card.querySelector('.return-oneway-info').textContent = formatFlightInfo(returnOneway);

    const roundTrip = flightData.roundTrip;
    card.querySelector('.roundtrip-price').textContent = formatPrice(roundTrip?.price);
    if (roundTrip) {
        const departureInfo = formatFlightInfo(roundTrip);
        const returnDate = new Date(roundTrip.returnDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        card.querySelector('.roundtrip-info').textContent = `${departureInfo} - Return ${returnDate}`;
    } else {
        card.querySelector('.roundtrip-info').textContent = 'No flights found';
    }
    
    // Set main origin and airline text
    if (outboundOneway) {
        card.querySelector('.origin').textContent = `From: ${outboundOneway.origin}`;
        let airlineText = `✈️ Airlines: ${outboundOneway.airline || 'N/A'}`;
        if (returnOneway && returnOneway.airline && returnOneway.airline !== outboundOneway.airline) {
            airlineText += ` / ${returnOneway.airline}`;
        }
        card.querySelector('.airline').textContent = airlineText;
    } else {
        card.querySelector('.origin').textContent = `From: --`;
        card.querySelector('.airline').textContent = `✈️ Airlines: --`;
    }
}

function handleSubscriptionForm() {
    // This function remains the same as before
    const form = document.getElementById('subscribe-form');
    const messageEl = document.getElementById('form-message');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = document.getElementById('email-input').value;
        const destination = document.getElementById('destination-select').value;
        
        messageEl.textContent = 'Subscribing...';
        messageEl.style.color = '#333';

        setTimeout(() => {
            messageEl.textContent = `Success! You'll be notified of price drops for ${destination}.`;
            messageEl.style.color = 'green';
            form.reset();
        }, 1000);
    });
}