
//Function for updating crypto values on the list of cryptocurrencies
function updateCryptocurrencyPrices() {
  // Create a list of currency symbols you're interested in
    const symbols = ["btc", "eth", "ada"]; // Example symbols

    // Format the symbols for WebSocket URL
    const formattedSymbols = symbols.map(symbol => `${symbol}usdt@aggTrade`).join('/');

    // Create the WebSocket URL with combined streams
    const socket = new WebSocket(`wss://stream.binance.com:9443/stream?streams=${formattedSymbols}`);

    socket.addEventListener("open", () => {
      console.log("WebSocket connection established");
    });

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);

      // Extract data for each currency pair
      const cryptoSymbol = message.stream.split('@')[0];
      const livePrice = parseFloat(message.data.p);
      console.log(cryptoSymbol);
      console.log(livePrice);

      // Update the price for the corresponding currency in your HTML
      const priceCells = document.querySelectorAll(`.${cryptoSymbol}-price`);
      priceCells.forEach(priceCell => {
        priceCell.innerHTML = livePrice.toFixed(2);
      });
    });


}




//Function for updating crypto values on the trade page
function passCryptoValues() {
  queryString2 = window.location.search;
  urlParams2 = new URLSearchParams(queryString2);
  symbol2 = urlParams2.get("symbol");
  name2 = urlParams2.get("name");
  currentPrice = urlParams2.get("current");
  document.getElementById("symbol-heading").innerHTML = symbol2.toUpperCase() + "(" + name2 +")";
  document.getElementById("price").value = currentPrice;
  document.getElementById("hidden-symbol").value = symbol2.toUpperCase() + "(" + name2 +")";
  document.getElementById("hidden-symbol2").value = symbol2.toUpperCase();
}

document.addEventListener("DOMContentLoaded", function() {
  passCryptoValues();

  var symbol = document.getElementById("hidden-symbol2").value;


  var socket = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}usdt@aggTrade`);

  socket.addEventListener("open", () => {
    console.log(symbol);
    console.log("Websocket2 Established");
  });

  socket.addEventListener("message", (event) => {
    var message = JSON.parse(event.data);
    console.log(message.p);
    data = parseFloat(message.p);
    document.getElementById("price").value = data.toFixed(5);
  });

  });


  document.addEventListener("DOMContentLoaded", function() {

    // Call the function to update cryptocurrency prices
    updateCryptocurrencyPrices();

  });



document.addEventListener('DOMContentLoaded', function() {


  var search =  document.getElementById("chart-search");
  document.addEventListener("keydown", function() {
    search.style.display = 'block';
  });

  window.addEventListener('click', function() {
      search.style.display = 'none';
  });

  var chart = LightweightCharts.createChart(document.getElementById('chart'), {
    width: 1338,
    height: 720,
    layout: {
      height: '100%',
      width: '100%',
      backgroundColor: '#fff',
      textColor: 'rgba(0, 0, 0, 0.9)',
      borderColor: '#000',
    },

    grid: {
      vertLines: {
        color: 'rgba(0, 0, 0, 0)', // Set vertical grid lines color to transparent (i.e., no lines)
      },
      horzLines: {
        color: 'rgba(0, 0, 0, 0)', // Set horizontal grid lines color to transparent (i.e., no lines)
      },
    },

  });

  var candleSeries = chart.addCandlestickSeries({
    upColor: 'rgba(255, 144, 0, 1)',
    downColor: '#000',
    borderColor: 'rgba(255, 144, 0, 1)',
    wickDownColor: 'rgba(255, 144, 0, 1)',
    wickUpColor: 'rgba(255, 144, 0, 1)',
  });


    var queryString = window.location.search;
    var urlParams = new URLSearchParams(queryString);
    var symbol = urlParams.get("symbol");
    var name = urlParams.get("name");
    var interval = "1m";
    var apiKey = "be2268685046f9c369db2f4a22e442d04ce4ea81415d4f97de65483edb5df25b";

    localStorage.setItem("symbol", symbol);
    localStorage.setItem("name", name);

    var symbol1 = localStorage.getItem("symbol");
    var name1 = localStorage.getItem("name");

    var heading = document.getElementById('symbol-heading');

    heading.innerHTML = symbol1.toUpperCase() + "(" + name1 + ")";


    var socket = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol}usdt@kline_${interval}`);

    socket.addEventListener("open", () => {
      console.log("WebSocket connection established");
    });

    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      console.log("Received message:", message);
      const klineData = message.k; // Use message.k to access Kline data

      var transformedData = {
        time: klineData.t * 1000, // Convert Unix timestamp to milliseconds
        open: parseFloat(klineData.o),
        high: parseFloat(klineData.h),
        low: parseFloat(klineData.l),
        close: parseFloat(klineData.c),
      };

      // Update the candleSeries with the new data
      candleSeries.update(transformedData);
    });



    fetch('https://min-api.cryptocompare.com/data/v2/histominute?fsym='+symbol1+'&tsym=USD&limit=2000&api_key=' + apiKey, {
      method: 'GET',
    })
      .then(response => response.json()) // Parse the response as JSON
      .then(data => {
        // Process the response data
        console.log(data);
        var jsonData = data.Data.Data;
        var transformedData = jsonData.map(function(candle) {
          return {
            time: candle.time * 1000, // Convert Unix timestamp to milliseconds
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
          };
        });

        candleSeries.setData(transformedData);
      })
      .catch(error => {
        // Handle any errors
        console.error("Error:", error);
      });
    });


    fetch("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")
        .then(response => response.json())
        .then(data => {
          const searchInput = document.getElementById("home-search");
          const searchBox = document.getElementById("search-container");

          function handlesearch() {
            var results = [];
            var symbols = {}
            for (var i = 0; i < data.length; i++) {
              results.push(data[i].name);
              symbols[data[i].name] = data[i].symbol;
            }

            const searchText = searchInput.value.toLowerCase();
            const filteredData = results.filter(item => item.toLowerCase().includes(searchText));

            searchBox.innerHTML = "";

            if (searchText.trim() !== '' && searchInput.value !== "") {
              filteredData.forEach(item => {
                const resultItem = document.createElement("a");
                resultItem.href = "/chart?name=" + item + "&symbol=" + symbols[item];
                resultItem.textContent = item;
                searchBox.appendChild(resultItem);

              });
            }
          }
          document.getElementById("home-search").addEventListener('input', handlesearch)

          document.addEventListener('click', function(event) {
            if (event.target !== searchInput && event.target !== searchBox) {
              searchBox.innerHTML = "";
            }
          });

        });