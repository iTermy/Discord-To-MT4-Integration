#property strict

#import "kernel32.dll"
    int CreateFileW(string lpFileName, uint dwDesiredAccess, uint dwShareMode, int lpSecurityAttributes, uint dwCreationDisposition, uint dwFlagsAndAttributes, int hTemplateFile);
    bool ReadFile(int hFile, uchar &lpBuffer[], uint nNumberOfBytesToRead, uint &lpNumberOfBytesRead, int lpOverlapped);
    bool WriteFile(int hFile, const uchar &lpBuffer[], uint nNumberOfBytesToWrite, uint &lpNumberOfBytesWritten, int lpOverlapped);
    bool SetFilePointer(int hFile, int lDistanceToMove, int &lpDistanceToMoveHigh, uint dwMoveMethod);
    bool SetEndOfFile(int hFile);
    bool CloseHandle(int hObject);
    uint GetLastError(void);
#import

#define GENERIC_READ 0x80000000
#define GENERIC_WRITE 0x40000000
#define FILE_SHARE_READ 0x00000001
#define FILE_SHARE_WRITE 0x00000002
#define OPEN_EXISTING 3
#define INVALID_HANDLE_VALUE -1
#define FILE_BEGIN 0

//-------------------------------------------+
// ONLY CHANGE THINGS INSIDE HERE
//-------------------------------------------+

string filename = "";
// Copy path to "connection.txt" inside the "". Example: string filename = "C:\\MyUser\\My bot\\connection.txt";
// IMPORTANT: When you copy and paste the path, only one \ will separate the folders.
// make sure you change it to have two '\'s for the path, or else it won't work properly. See example.

string defaultSettingsPath = "";
// Do the same as above, but for default_settings.txt

string pendingOrdersPath = "";
// Do the same as above, but for active_orders.txt

//-------------------------------------------+
// ONLY CHANGE THINGS INSIDE HERE
//-------------------------------------------+

// Global variables
string lastContent = "";
bool tradeinProgress = false;
int interval = 10;
int countSecs = 8;
double lotsize;

// Default Settings Initialization
string autospread;
string autolot;
double defaultlotsize;
string risk;

int OnInit()
{
    EventSetTimer(1);
    ProcessDefaultSettings(defaultSettingsPath);
    lotsize = defaultlotsize;
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}
void OnTimer()
{
     countSecs++;
     if (countSecs >= interval)
     {
      ProcessDefaultSettings(defaultSettingsPath);
      ClearFile(pendingOrdersPath);
      WritePendingLimitsToFile();
      countSecs = 0;
     }
     
     string fileContent = ReadFileOutsideSandbox(filename);

      // COMMANDS: All processed from connection.txt
     if ((StringLen(fileContent) > 0) && (fileContent != lastContent))
     {
      string command = ProcessCommand(fileContent);
      
      if (command == "changeLot")
      {
         ChangeLotSize(fileContent);
      }
      
      else if (command == "addLimits" && !tradeinProgress)
      {
         tradeinProgress = true;
         ProcessLimits(fileContent, lotsize);
         tradeinProgress = false;
      }
      
      else if (command == "deleteOrder")
      {
         DeletePendingLimits(fileContent);
      }
      else if (command == "deleteAll")
      {
         DeleteAllPendingOrders();
      }
      else
      {
         Print("Invalid command used!");
      }
     }
}
// -------------------------------
// HELPER FUNCTIONS
// -------------------------------
string ReadFileOutsideSandbox(string file_path)
{
    int fileHandle = CreateFileW(file_path, GENERIC_READ| GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, 0, OPEN_EXISTING, 0, 0);
    
    if (fileHandle == INVALID_HANDLE_VALUE) {
        uint errorCode = GetLastError();
        Print("Error: Unable to open the file. Error code: ", errorCode);
        return "FAILED";
    }
    
    uchar buffer[];
    ArrayResize(buffer, 1024);
    uint bytesRead = 0;
    
    if (ReadFile(fileHandle, buffer, ArraySize(buffer) - 1, bytesRead, 0)) {
        buffer[bytesRead] = 0;
        string content = CharArrayToString(buffer, 0, bytesRead, CP_ACP);
        
        // Clear the file after reading
        int filePointer = 0;
        SetFilePointer(fileHandle, 0, filePointer, FILE_BEGIN);
        SetEndOfFile(fileHandle);
        CloseHandle(fileHandle);
        return content;
        
    } else {
        Print("Error: Unable to read the file. Error code: ", GetLastError());
        CloseHandle(fileHandle);
        return "FAILED";
    }
}

void WriteFileOutsideSandbox(string filepath, string content)
{
    int fileHandle = CreateFileW(filepath, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, 0, OPEN_EXISTING, 0, 0);
    
    if (fileHandle == INVALID_HANDLE_VALUE) {
        uint errorCode = GetLastError();
        Print("Error: Unable to open the file for writing. Error code: ", errorCode);
        return;
    }
    
    uchar buffer[];
    int bufferSize = StringToCharArray(content, buffer, 0, WHOLE_ARRAY, CP_UTF8);
    uint bytesWritten = 0;
    
    if (WriteFile(fileHandle, buffer, bufferSize - 1, bytesWritten, 0)) {
        // Print("Successfully wrote ", bytesWritten, " bytes to the file.");
    } else {
        Print("Error: Unable to write to the file. Error code: ", GetLastError());
    }
    
    CloseHandle(fileHandle);
}

string ProcessCommand(string &fileContent)
{
   string lines[];
   StringSplit(fileContent, '\n', lines);
   
   if (ArraySize(lines) == 0)
   {
      return "";
   }
   
   string command = StringTrimRight(StringTrimLeft(lines[0]));
   
   // Remove the first line from fileContent
   fileContent = "";
   for (int i = 1; i < ArraySize(lines); i++)
   {
      fileContent += lines[i] + (i < ArraySize(lines) - 1 ? "\n" : "");
   }
    
   return command;
}

string ReadDefaultSettingsFile(string file_path)
{
    int fileHandle = CreateFileW(file_path, GENERIC_READ| GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, 0, OPEN_EXISTING, 0, 0);
    
    if (fileHandle == INVALID_HANDLE_VALUE) {
        uint errorCode = GetLastError();
        Print("Error: Unable to open the file. Error code: ", errorCode);
        return "FAILED";
    }
    
    uchar buffer[];
    ArrayResize(buffer, 1024);
    uint bytesRead = 0;
    
    if (ReadFile(fileHandle, buffer, ArraySize(buffer) - 1, bytesRead, 0)) {
        buffer[bytesRead] = 0;
        string content = CharArrayToString(buffer, 0, bytesRead, CP_ACP);
        CloseHandle(fileHandle);
        return content;
        
    } else {
        Print("Error: Unable to read the file. Error code: ", GetLastError());
        CloseHandle(fileHandle);
        return "FAILED";
    }
}

void ProcessDefaultSettings(string settingsPath)
{
   string defaultContent = ReadDefaultSettingsFile(settingsPath);
   string lines[];
   int lineCount = StringSplit(defaultContent, '\n', lines);
   for (int i = 0; i < lineCount; i++)
   {
      string line = StringTrimRight(StringTrimLeft(lines[i]));
        if (StringLen(line) > 0)
        {
            ProcessSettingLine(line);
        }
   }
}

void ProcessSettingLine(string line)
{
    string parts[];
    int partCount = StringSplit(line, ' ', parts);
    
    if (partCount != 2)
    {
        Print("Invalid format: ", line);
        return;
    }
    
    string setting = parts[0];
    string state = parts[1];
    
    if (setting == "autospread")
    {
      autospread = state;
    }
    
    if (setting == "autolot")
    {
      autolot = state;
    }
    
    if (setting == "defaultlotsize")
    {
      defaultlotsize = NormalizeDouble(float(state), 2);
    }
    
    if (setting == "risk")
    {
      risk = state;
    }

}

// Function to calculate distance based on instrument type
double CalculateDistance(string symbol, double currentPrice, double limitPrice)
{
    double pointValue = MarketInfo(symbol, MODE_POINT);
    double distance = MathAbs(currentPrice - limitPrice);
    
    if(symbol == "XAUUSD" || symbol == "XAGUSD")
    {
        return distance;  // For gold and silver, return the direct price difference
    }
    else if(symbol == "US100" || symbol == "US500" || symbol == "GER30" || symbol == "US30")
    {
        return distance;  // For indices, return the direct price difference
    }
    else if(symbol == "BTCUSD" || symbol == "WTI")
    {
        return distance;  // For Bitcoin and Oil, return the direct price difference
    }
    else // Forex pairs and other instruments
    {
        return distance / pointValue;  // Convert to pips
    }
}

// Function to get the appropriate number of decimal places for price formatting
int GetPriceDecimals(string symbol)
{
    if(symbol == "XAUUSD" || symbol == "XAGUSD") return 2;
    if(symbol == "US100" || symbol == "US500" || symbol == "GER30" || symbol == "US30") return 0;
    if(symbol == "BTCUSD") return 1;
    if(symbol == "WTI") return 2;
    return (int)MarketInfo(symbol, MODE_DIGITS);  // For forex pairs and other instruments
}

// Function to write pending limit orders to file
void WritePendingLimitsToFile()
{
    string content = "";
    int total = OrdersTotal();
    
    for(int i = 0; i < total; i++)
    {
        if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
        {
            if(OrderType() == OP_BUYLIMIT || OrderType() == OP_SELLLIMIT)
            {
                string symbol = OrderSymbol();
                string direction = (OrderType() == OP_BUYLIMIT) ? "LONG" : "SHORT";
                int priceDecimals = GetPriceDecimals(symbol);
                double limitPrice = NormalizeDouble(OrderOpenPrice(), priceDecimals);
                double stopLoss = NormalizeDouble(OrderStopLoss(), priceDecimals);
                double currentPrice = MarketInfo(symbol, MODE_BID);
                double distance = CalculateDistance(symbol, currentPrice, limitPrice);
                
                string distanceUnit = (symbol == "XAUUSD" || symbol == "XAGUSD" || 
                                       symbol == "US100" || symbol == "US500" || 
                                       symbol == "GER30" || symbol == "US30" || 
                                       symbol == "BTCUSD" || symbol == "WTI") ? "$" : "pips";
                
                string limitPriceStr = DoubleToString(limitPrice, priceDecimals);
                string stopLossStr = DoubleToString(stopLoss, priceDecimals);
                string distanceStr = DoubleToString(distance, 2);
                
                content += StringFormat("%s %s %s %s %s%s\n", 
                                        symbol, direction, limitPriceStr, 
                                        stopLossStr, distanceStr, distanceUnit);
            }
        }
    }
    
    if(content != "")
    {
        WriteFileOutsideSandbox(pendingOrdersPath, content);
    }
}

bool ClearFile(string file_path)
{
    int fileHandle = CreateFileW(file_path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, 0, OPEN_EXISTING, 0, 0);
    
    if (fileHandle == INVALID_HANDLE_VALUE) {
        uint errorCode = GetLastError();
        Print("Error: Unable to open the file for writing. Error code: ", errorCode);
        return false;
    }
    
    // Move file pointer to the beginning
    int high = 0;
    SetFilePointer(fileHandle, 0, high, FILE_BEGIN);
    
    // Set end of file at current position (beginning), effectively clearing the file
    if (!SetEndOfFile(fileHandle)) {
        Print("Error: Unable to clear the file. Error code: ", GetLastError());
        CloseHandle(fileHandle);
        return false;
    }
    
    CloseHandle(fileHandle);
    // Print("File cleared successfully");
    return true;
}

//----------------------------------------------
// CHANGE LOT SIZE COMMAND
// ---------------------------------------------
void ChangeLotSize(string &fileContent)
{
   lotsize = StringToDouble(fileContent);
   Print("New lot size is: ", lotsize);
}


// ---------------------------------------------
// PROCESS LIMITS COMMAND
// --------------------------------------------
void ProcessLimits(string content, double LotSize)
{
    double manualLot = LotSize;
    double autoSizedLot;
    string lines[];
    double totalPipStopLoss = 0;
    string symbol;
    double balance = AccountBalance();
    int lineCount = StringSplit(content, '\n', lines);
    
    for (int i = 0; i < lineCount; i++)
    {
        string line = StringTrimRight(StringTrimLeft(lines[i]));
        if (StringLen(line) > 0)
        {
          if (autolot == "off")
          {
            ProcessOrderLine(line, manualLot);
          }
          if (autolot == "on")
          {
            string parts[];
            int partCount = StringSplit(line, ' ', parts);
            if (partCount != 4)
            {
               Print("Invalid order line format: ", line);
               return;
            }
            symbol = parts[1];
            double price = StringToDouble(parts[0]); // PAIR: Example: 0.86668
            double stopLoss = StringToDouble(parts[3]); // PAIR: Example: 0.86966
            totalPipStopLoss += MathAbs(stopLoss - price); // PAIR: Example: 0.00298
          }
        }
    }
    
    if (autolot == "on")
    {
      // USDJPY Lot calculation
      if (symbol == "USDJPY")
      {
         totalPipStopLoss = MathRound(totalPipStopLoss * 100);
         Print("The total pip loss would be " + string(totalPipStopLoss) + " pips or " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
      
         autoSizedLot = NormalizeDouble(((balance * ((double)risk / 100 )) / (totalPipStopLoss * (0.01 / (MarketInfo(symbol, MODE_ASK))))/100000) / (double)lineCount, 2);
         Print("Lots per limit is", autoSizedLot);
         // ((Account size * (Risk % / 100 )) / (SL Pips * (0.01 / USDJPY price))/100000)  / # of limits
      }
      
      
      else if (symbol == "XAUUSD")
      {
         Print("In the case of stop loss, " + symbol + " will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble(((balance * double(risk) / 100) / (totalPipStopLoss * 100) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 100) / # of limits
      }
      
      else if (symbol == "US100")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble(((balance * double(risk) / 100) / (totalPipStopLoss * 20) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 20) / # of limits
      }
      
      else if (symbol == "WTI")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble((((balance * double(risk) / 100) / (totalPipStopLoss * 1000)) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 1000) / # of limits
      }
      
      else if (symbol == "US500")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble((((balance * double(risk) / 100) / (totalPipStopLoss * 50)) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 50) / # of limits
      }
      
      else if (symbol == "GER30")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble((((balance * double(risk) / 100) / (totalPipStopLoss * 27)) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 27) / # of limits
      }
      
      else if (symbol == "US30")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble((((balance * double(risk) / 100) / (totalPipStopLoss * 5)) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 5) / # of limits
      }
      
      else if (symbol == "XAGUSD")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble((((balance * double(risk) / 100) / (totalPipStopLoss * 5000)) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 5000) / # of limits
      }
      
      else if (symbol == "BTCUSD")
      {
         Print("In the case of stop loss, " + symbol + "will go $" + (string)NormalizeDouble(totalPipStopLoss, 2) + " against you and you will lose " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble((((balance * double(risk) / 100) / (totalPipStopLoss * 1)) / (double)lineCount), 2);
         // Lot Size = (Account size * (Risk / 100)) / (SL in dollars * 1) / # of limits
      }
      
      // Regular forex pair lot calculation
      else
      {
         totalPipStopLoss = MathRound(totalPipStopLoss * 10000);
         Print("The total pip loss would be " + string(totalPipStopLoss) + " pips or " + (string)MathRound((balance * (double(risk)))/100) + " dollars.");
         autoSizedLot = NormalizeDouble(((((balance * (double)risk / 100)/(totalPipStopLoss * 0.1))/100)) / (double)lineCount, 2);
         // ((Account size x Risk /100)/(Avg Sl*0.1))/100 / # of limits
      }

      for (int i = 0; i < lineCount; i++)
      {
         string line = StringTrimRight(StringTrimLeft(lines[i]));
         if (StringLen(line) > 0)
         {
            ProcessOrderLine(line, autoSizedLot);
         }
      }
    }
}

void ProcessOrderLine(string line, double LotSize)
{
    double currLot = LotSize;
    string parts[];
    int partCount = StringSplit(line, ' ', parts);
    
    if (partCount != 4)
    {
        Print("Invalid order line format: ", line);
        return;
    }
    
    double price = StringToDouble(parts[0]);
    string symbol = parts[1];
    string direction = parts[2];
    double stopLoss = StringToDouble(parts[3]);
    
    if (price <= 0 || stopLoss <= 0)
    {
        Print("Invalid price or stop loss in line: ", line);
        return;
    }
    
    int orderType;
    if (direction == "LONG")
        orderType = OP_BUYLIMIT;
    else if (direction == "SHORT")
        orderType = OP_SELLLIMIT;
    else
    {
        Print("Invalid direction in line: ", line);
        return;
    }
    
    PlaceLimitOrder(symbol, orderType, price, stopLoss, LotSize);
}

void PlaceLimitOrder(string symbol, int orderType, double price, double stopLoss, double LotSize)
{
    // Calculates stop loss
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double spread = (ask - bid) / point;
    
    double adjustedPrice = price;
    double adjustedStopLoss = stopLoss;
    double currLot = LotSize;
    
    if (orderType == OP_BUYLIMIT)
    {
      if (autospread == "on")
      {
        adjustedPrice = NormalizeDouble(price + spread * point, digits);
        adjustedStopLoss = NormalizeDouble(stopLoss, digits);
      }
      else
      {
        adjustedPrice = NormalizeDouble(price, digits);
        adjustedStopLoss = NormalizeDouble(stopLoss, digits);
      }
    }
    else if (orderType == OP_SELLLIMIT)
    {
      if (autospread == "on")
      {
        adjustedPrice = NormalizeDouble(price - spread * point, digits);
        adjustedStopLoss = NormalizeDouble(stopLoss, digits);
      }
      else
      {
        adjustedPrice = NormalizeDouble(price, digits);
        adjustedStopLoss = NormalizeDouble(stopLoss, digits);
      }
    }
    else
    {
        Print("Error: Invalid order type for ", symbol);
        return;
    }
    
    int ticket = OrderSend(symbol, orderType, currLot, adjustedPrice, 3, adjustedStopLoss, 0, "Discord order", 0, 0, clrNONE);
    
    if (ticket > 0)
        Print("Order placed successfully: ", symbol, " ", EnumToString((ENUM_ORDER_TYPE)orderType), " at ", adjustedPrice, " with SL ", adjustedStopLoss);
    else
        Print("Error placing order: ", GetLastError());
}

// ---------------------------
// DELETE ORDER COMMAND
// ---------------------------
void DeletePendingLimits(string message)
{
    string symbol = "";
    string direction = "";
    double stopLoss = 0;
    double limits[];
    
    // Parse the input string
    string parts[];
    StringSplit(message, ' ', parts);
    
    if (ArraySize(parts) < 5)
    {
        Print("Invalid input format");
        return;
    }
    
    symbol = parts[0];
    direction = parts[1];
    
    int limitCount = 0;
    for (int i = 2; i < ArraySize(parts); i++)
    {
        if (parts[i] == "stops")
        {
            if (i + 1 < ArraySize(parts))
            {
                stopLoss = StringToDouble(parts[i+1]);
            }
            break;
        }
        
        ArrayResize(limits, limitCount + 1);
        limits[limitCount] = StringToDouble(parts[i]);
        limitCount++;
    }
    
    // Delete matching pending orders
    for (int i = OrdersTotal() - 1; i >= 0; i--)
    {
        if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
        {
            if (OrderSymbol() == symbol && 
                ((direction == "long" && OrderType() == OP_BUYLIMIT) || 
                 (direction == "short" && OrderType() == OP_SELLLIMIT)))
            {
                for (int j = 0; j < limitCount; j++)
                {
                    if (NormalizeDouble(OrderOpenPrice(), Digits) == NormalizeDouble(limits[j], Digits) &&
                        NormalizeDouble(OrderStopLoss(), Digits) == NormalizeDouble(stopLoss, Digits))
                    {
                        bool result = OrderDelete(OrderTicket());
                        if (result)
                            Print("Order deleted: Ticket ", OrderTicket());
                        else
                            Print("Failed to delete order: Ticket ", OrderTicket(), ", Error ", GetLastError());
                        break;
                    }
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Function to delete all pending orders for all symbols            |
//+------------------------------------------------------------------+
void DeleteAllPendingOrders()
{
   int total = OrdersTotal();
   
   for (int i = total - 1; i >= 0; i--)
   {
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if (OrderType() > OP_SELL)  // Check if it's a pending order
         {
            bool result = OrderDelete(OrderTicket());
            
            if (!result)
            {
               Print("Error deleting order ", OrderTicket(), " for ", OrderSymbol(), ": ", GetLastError());
            }
            else
            {
               Print("Deleted pending order ", OrderTicket(), " for ", OrderSymbol());
            }
         }
      }
   }
}