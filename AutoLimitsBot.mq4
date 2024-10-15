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

// ---------------------------------------------
// ***** ONLY CHANGE THINGS INSIDE HERE ***** //

string filename = "";
// Copy path to "connections.txt" inside the "". Example: string filename = "C:\\MyUser\\My bot\\connection.txt";
// IMPORTANT: When you copy and paste the path, only one \ will separate the folders.
// make sure you change it to have two '\'s for the path, or else it won't work properly. See example.


string lot_size_file = "";
// Do the same as above, but for lot_size.txt


// To disable auto-spread adjustment, follow instructions on lines 197-203 */

// ---------------------------------------------

string lastContent = "";
double lastLot = 0.01;
bool tradeinProgress = false; 

int OnInit()
{
    EventSetTimer(1);
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}
void OnTimer()
{
     string fileContent = ReadFileOutsideSandbox(filename);
     double lotFileContent = (double)ReadFileOutsideSandbox(lot_size_file);
     
     if (lotFileContent != lastLot)
      {
         lastLot = lotFileContent;
         Print("Lot size changed to ", lastLot);
      }
      

     if ((StringLen(fileContent) > 0) && (fileContent != lastContent) && (tradeinProgress == false))
     {
      tradeinProgress = true;
      Print("File content found: ", fileContent);
      ProcessFileContent(fileContent, lastLot);
      ClearFile(filename);
      tradeinProgress = false;
     }
}
void OnTick()
{ 
}

string ReadFileOutsideSandbox(string file_path)
{
    int fileHandle = CreateFileW(file_path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, 0, OPEN_EXISTING, 0, 0);
    
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
    Print("File cleared successfully");
    return true;
}

void ProcessFileContent(string content, double LotSize)
{
    double currLot = LotSize;
    string lines[];
    int lineCount = StringSplit(content, '\n', lines);
    
    for (int i = 0; i < lineCount; i++)
    {
        string line = StringTrimRight(StringTrimLeft(lines[i]));
        if (StringLen(line) > 0)
        {
            ProcessOrderLine(line, currLot);
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
        adjustedPrice = NormalizeDouble(price + spread * point, digits); // REMOVE " + spread * point" FOR MANUAL SPREAD CALCULATION
        adjustedStopLoss = NormalizeDouble(stopLoss + spread * point, digits); // REMOVE " + spread * point" FOR MANUAL SPREAD CALCULATION
    }
    else if (orderType == OP_SELLLIMIT)
    {
        adjustedPrice = NormalizeDouble(price - spread * point, digits); // REMOVE " - spread * point" FOR MANUAL SPREAD CALCULATION
        adjustedStopLoss = NormalizeDouble(stopLoss - spread * point, digits); // REMOVE " - spread * point" FOR MANUAL SPREAD CALCULATION
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
