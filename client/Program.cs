using System;
using System.Text;
using System.IO;
using System.Numerics;
using Appccelerate.CommandLineParser;
using Neo;
using Neo.SmartContract;
using Neo.Network.P2P.Payloads;
using Neo.Network.RPC;
using Neo.VM;
using Neo.Wallets;
using System.Threading.Tasks;
using Neo.Network.RPC.Models;

namespace client;

public class Program
{
    public static void Main(string[] args)
    {
        MainAsync(args).GetAwaiter().GetResult();
    }

    public static async Task MainAsync(string[] args)
    {
        bool mint = false;
        string wif = "L4DbWZksqcGgq7fmMjjt8EVHi5FjR89ePsmTJMEu5Ndjf2JgEtTD";
        string rpcUrl = "http://localhost:50012";
        UInt160 contract = UInt160.Parse("bb6e85b760664e6df28532417b3dbf1d33c02418");
        ProtocolSettings settings = ProtocolSettings.Load("config.json");

        var configuration = CommandLineParserConfigurator
            .Create()
                .WithSwitch("m", () => mint = true)
                    .HavingLongAlias("mint")
                    .DescribedBy("Mints a random NFT")
                .WithNamed("w", v => wif = v)
                    .HavingLongAlias("wif")
                    .DescribedBy("WIF", "The WIF used to mint")
                .WithNamed("r", v => wif = v)
                    .HavingLongAlias("rpc")
                    .DescribedBy("RPC", "The RPC node to connect to")
                .WithNamed("c", v => contract = UInt160.Parse(v))
                    .HavingLongAlias("contract")
                    .DescribedBy("contract", "The contract to mint on")
            .BuildConfiguration();

        var parser = new CommandLineParser(configuration);
        var parseResult = parser.Parse(args);

        if (!parseResult.Succeeded)
        {
            Usage usage = new UsageComposer(configuration).Compose();
            Console.WriteLine(parseResult.Message);
            Console.WriteLine("usage:" + usage.Arguments);
            Console.WriteLine("options");
            Console.WriteLine(usage.Options.IndentBy(4));
            Console.WriteLine();

            return;
        }

        BigInteger nftId = BigInteger.Zero;
        if (mint)
        {
            nftId = await Mint(rpcUrl, wif, contract, settings);
        }

        if (nftId != BigInteger.Zero)
        {
            await QueryNft(nftId, rpcUrl, wif, contract, settings);
        }
    }

    private static async Task QueryNft(BigInteger nftId, string rpc, string wif, UInt160 contract, ProtocolSettings settings)
    {
        RpcClient client = new RpcClient(new Uri(rpc), null, null, settings);

        KeyPair sendKey = Neo.Network.RPC.Utility.GetKeyPair(wif);

        UInt160 sender = Contract.CreateSignatureContract(sendKey.PublicKey).ScriptHash;

        var base64num = Convert.ToBase64String(nftId.ToByteArray());
        RpcStack data = new RpcStack()
        {
            Type = "ByteArray",
            Value = base64num
        };
        
        Signer signer0 = new Signer()
        {
            Account = UInt160.Zero
        };
        
        RpcInvokeResult rpcInvokeResult = await client.InvokeFunctionAsync(contract.ToString(), "properties", new RpcStack[] { data }, signer0);
        if (!string.IsNullOrEmpty(rpcInvokeResult.Exception))
        {
            Console.WriteLine("Exception: " + rpcInvokeResult.Exception);
        }

        var stackItem = (Neo.VM.Types.Map)rpcInvokeResult.Stack[0];

        foreach (var item in stackItem)
        {
            var key = item.Key.GetString();
            var value = item.Value.GetString();

            if (key == "ascii")
            {
                Console.WriteLine( key + $" : \n" + item.Value.GetString());
            }
            else
            {
                Console.WriteLine( key + $" : " + item.Value.GetString());
            }

            Console.WriteLine();
        }
    }

    private static async Task<BigInteger> Mint(string rpc, string wif, UInt160 contract, ProtocolSettings settings)
    {
        RpcClient client = new RpcClient(new Uri(rpc), null, null, settings);

        KeyPair sendKey = Neo.Network.RPC.Utility.GetKeyPair(wif);

        UInt160 sender = Contract.CreateSignatureContract(sendKey.PublicKey).ScriptHash;

        Signer[] cosigners = new[] { new Signer { Scopes = WitnessScope.CalledByEntry, Account = sender } };

        var meta = @"{""name"":""some"", ""description"":""Test description"",""image"":""ipfs://example_ipfs_hash"",""tokenURI"":""""}";
        var metaBytes = Encoding.UTF8.GetBytes(meta);  

        var locked = @"something";
        var lockedBytes = Encoding.UTF8.GetBytes(locked);  

        var royalties = @"";
        var royaltiesBytes = Encoding.UTF8.GetBytes(royalties);  

        var asciiImage = File.ReadAllText("ascii_image.txt");
        Console.WriteLine(asciiImage);

        byte[] script = contract.MakeScript("mint", sender, metaBytes, lockedBytes, royaltiesBytes, asciiImage);

        TransactionManager txManager = await new TransactionManagerFactory(client).MakeTransactionAsync(script, cosigners).ConfigureAwait(false);

        Transaction tx = await txManager.AddSignature(sendKey).SignAsync().ConfigureAwait(false);

        await client.SendRawTransactionAsync(tx).ConfigureAwait(false);

        Console.WriteLine($"Transaction {tx.Hash.ToString()} is broadcasted!");

        WalletAPI neoAPI = new WalletAPI(client);
        await neoAPI.WaitTransactionAsync(tx)
           .ContinueWith(async (p) => Console.WriteLine($"Transaction included in block {(await p).BlockHash}"));

        var appLog = await client.GetApplicationLogAsync(tx.Hash.ToString(), TriggerType.Application);
        var nftId = appLog.Executions[0].Stack[0].GetInteger();

        Console.WriteLine($"Minted nft #{nftId}");

        return nftId;
    }
}
