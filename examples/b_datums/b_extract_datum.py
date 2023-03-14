# This is an example of how to determine the structure of the datum files to use with you eopsin custom datums.
# i.e. so that you can call the contract like on the previous example
# The JSON file is usually required by third party tools like the cardano-cli

# Import the dataclass from the eopsin python file

from examples.b_datums.a_complex_datum import BatchOrder, Withdraw, PubKeyHash

# Create the datum structure in the correct order and print it to use in your transactions for locking unlocking in cardano-cli
datum = BatchOrder(
    PubKeyHash(bytes.fromhex("0000000000000000000000000000000000")),
    Withdraw(
        1000000,
        20,
    ),
)

# Export in JSON notation
print(datum.to_json(indent=2))
"""
{
  "constructor": 0,
  "fields": [
    {
      "bytes": "0000000000000000000000000000000000"
    },
    {
      "constructor": 1,
      "fields": [
        {
          "int": 1000000
        },
        {
          "int": 20
        }
      ]
    }
  ]
}
"""
# Export as CBOR Hex
print(datum.to_cbor(encoding="hex"))
"""
d8799f510000000000000000000000000000000000d87a9f1a000f424014ffff
"""
