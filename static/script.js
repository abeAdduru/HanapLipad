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
    const originEl = card.querySelector('.origin');
    const airlineEl = card.querySelector('.airline');

    // Helper function to format prices into Japanese Yen
    const formatPrice = (price) => new Intl.NumberFormat('ja-JP', { 
        style: 'currency', 
        currency: 'JPY', 
        minimumFractionDigits: 0, 
        maximumFractionDigits: 0 
    }).format(price);

    // Helper function to format dates into a readable format
    const formatDate = (dateStr) => new Date(dateStr).toLocaleDateString('en-US', {
        month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC'
    });

    // --- Update One-Way Section ---
    if (flightData.oneWay) {
        card.querySelector('.one-way-price').textContent = formatPrice(flightData.oneWay.price);
        card.querySelector('.one-way-date').textContent = formatDate(flightData.oneWay.date);
        originEl.textContent = `From: ${flightData.oneWay.origin}`;
        airlineEl.textContent = flightData.oneWay.airline;
    } else {
        card.querySelector('.one-way-price').textContent = 'N/A';
        card.querySelector('.one-way-date').textContent = 'No flights found';
        airlineEl.textContent = ''; // Clear airline if no one-way flight
    }

    // --- Update Round-Trip Section ---
    if (flightData.roundTrip) {
        card.querySelector('.round-trip-price').textContent = formatPrice(flightData.roundTrip.price);
        const returnDate = new Date(flightData.roundTrip.returnDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        card.querySelector('.round-trip-date').textContent = `${formatDate(flightData.roundTrip.date)} - ${returnDate}`;
        
        // If one-way was not found, set origin/airline from round-trip data
        if (!flightData.oneWay) { 
            originEl.textContent = `From: ${flightData.roundTrip.origin}`;
            airlineEl.textContent = flightData.roundTrip.airline;
        }
    } else {
        card.querySelector('.round-trip-price').textContent = 'N/A';
        card.querySelector('.round-trip-date').textContent = 'No flights found';
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