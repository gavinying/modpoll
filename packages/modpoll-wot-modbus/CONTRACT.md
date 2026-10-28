# Experimental acquisition contract 0.1

This contract is for Modpoll configuration replacement. It is not a W3C Modbus
binding and does not claim support for arbitrary TM/TD. W3C structural validity
and executable acquisition validity are checked separately, using local schemas.
The namespace is reserved for this project; its documentation is not published yet.

| 1.x CSV field | Contract 0.1 |
| --- | --- |
| device name | TM/TD title; preserve effective output name |
| Unit ID | Explicit load_model unit_id parameter, default 1, range 1–254 (legacy range) |
| poll table/start/count | acquisition table/start/quantity; literal PDU addresses |
| poll endian | byteOrder BE_BE, BE_LE, LE_BE, LE_LE |
| ref name | property key and member property reference |
| ref address | register offset from poll start; bit tables use eight-bit group offsets |
| ref `address:bit` | member bit, 0–15, register bool only |
| ref dtype | integer, float, bool/bool8/bool16, stringN |
| ref rw | standard readOnly/writeOnly; neither means rw |
| ref unit | standard property unit |
| ref scale | member multiplier; decimal multiplier, never inferred as divisor |

Block order, boundaries and gaps are preserved. Coils and DI count physical bits;
legacy bit-member offsets count eight-bit groups. This asymmetry is explicit to
preserve 1.x behavior. Register offsets count 16-bit registers; stringN lengths
count bytes. Read-only tables require readOnly, correcting the sample CSV's rw
labels rather than promising unsupported writes. Shared backing addresses are
permitted; duplicate property membership is rejected. No automatic coalescing,
TM inheritance, placeholder substitution, remote context resolution or protocol
execution is performed by this layer. Unsupported semantics are deliberately rejected or excluded; runtime integration
and instantiation of protocol forms remain subsequent work.

The modsim fixture is an explicitly authored mapping of modpoll/examples/modsim.csv,
including its full 44-register holding group and 37 output properties. It does not
claim the default server is generated from the fixture. Standard schema success
alone does not verify decoding, write commands or device behavior.
