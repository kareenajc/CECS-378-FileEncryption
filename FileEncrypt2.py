import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, asymmetric
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac, serialization
import json


CONST_RSA_KEY_SIZE = 2048
CONST_INDENT_SIZE = 4
CONST_PADDING_BITS = 128
constants = 32
def MyEncrypt(message, key):
    #checking key length
    if(len(key) < 32):
        raise ValueError("Key less than 32 Bytes!")
    
    #assigning values
    IVLength = 16
    IV = os.urandom(IVLength)
    backend = default_backend()
    
    #initialize padder
    padder = padding.PKCS7(128).padder()
    
    #pad data to fit block size
    message = padder.update(message) + padder.finalize()
    
    #create cipher object
    cipher = Cipher(algorithms.AES(key), modes.CBC(IV), backend=backend)
    
    #make encryptor
    encryptor = cipher.encryptor()
    
    #encrypt message
    C = encryptor.update(message) + encryptor.finalize()
    return C, IV

def MyFileEncrypt(filepath):
    #generating key
    keylength = 32
    key = os.urandom(keylength)
    
    #getting file name and extension
    filename_ext = os.path.basename(filepath) #gets file name with extension from path
    filename, ext = os.path.splitext(filename_ext) #separates file name and extension
    
    #reading file
    file = open(filepath, "rb")
    m = file.read()
    file.close()
    
    #calling encryption method
    C, IV = MyEncrypt(m, key)
    
    file = open(filepath, "wb")
    file.write(C)
    file.close()
    
    return C, IV, key, ext



def MyEncryptMAC(message, EncKey, HMACKey):
    
    #get ciphertext and IV
    C, IV = MyEncrypt(message, EncKey)
    
    #create HMAC object to make tag
    h = hmac.HMAC(HMACKey, hashes.SHA256(), backend=default_backend())
    h.update(C)
    tag = h.finalize()
    
    return C, IV, tag


def MyFileEncryptMAC(filepath):
    
    #create Keys
    KeyLength = 32
    HMACKey = os.urandom(KeyLength)
    EncKey = os.urandom(KeyLength)
    
    if len(EncKey) < KeyLength:
        raise Exception("EncKey less than 32 bytes!")
    if len(HMACKey) < KeyLength:
        raise Exception("HMACKey less than 32 bytes!")
    
    #open and read file to encrypt
    file = open(filepath, "rb")
    m = file.read()
    file.close()
    
    #getting file name and extension
    filename_ext = os.path.basename(filepath) #gets file name with extension from path
    filename, ext = os.path.splitext(filename_ext) #separates file name and extension
    
    #encrypt & MAC
    C, IV, tag = MyEncryptMAC(m, EncKey, HMACKey)
    
    #storing values
    encData = {"C": C.decode('cp437'), "IV": IV.decode('cp437'), "EncKey": EncKey.decode('cp437'), "ext": ext, "tag": tag.decode('cp437')}
    
    #create and write to json
    filenameJSON = filename + ".json"
    
    #write json data to file
    with open(filenameJSON, "w") as outfile:
        json.dump(encData, outfile)
        outfile.close()
    
        

    #delete original file
    os.remove(filepath)
    
    return C, IV, tag, EncKey, HMACKey, ext
#--------------
    # RSA Encrypt using AES CBC 256 Encryption with HMAC 
def myRSAEncrypt(filepath, RSA_Publickey_filepath):

	(C, IV, tag, EncKey, HMACKey, ext) = MyFileEncryptMAC(filepath)
	
	key = EncKey + HMACKey

	with open(RSA_Publickey_filepath, 'rb') as key_file:
		public_key = serialization.load_pem_public_key(
			key_file.read(),
			backend = default_backend()
			)

		RSACipher = public_key.encrypt(
			key,
			asymmetric.padding.OAEP(
				mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
				algorithm=hashes.SHA256(),
				label=None
				)
			)
		key_file.close()

	return (RSACipher, C, IV, tag, ext) 
   

		

# AES requires plain text and ciphertext to be a multiple of 16
# We pad it so that the message is a multiple of the IV, 16
def addPadding(encoded):
	
	# We pad it with 128 bits or 16 bytes
	padder = padding.PKCS7(constants.CONST_PADDING_BITS).padder()

	# update() pads the encoded message
	padded_encoded = padder.update(encoded)

	# .finalize () Returns the remainder of the data.
	padded_encoded += padder.finalize()
	return padded_encoded  
   
   


def MyDecrypt(C, IV, key):
    #make cipher
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(IV), backend=backend)
    
    #make decryptor
    decryptor = cipher.decryptor()
    
    #decrypt ciphertext
    plaintext_padded = decryptor.update(C) + decryptor.finalize()

    

    #unpad message
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(plaintext_padded) + unpadder.finalize()
    
    return plaintext

def MyFileDecrypt(filepath, IV, key, ext):

    #getting file name and extension

     #getting file name and extension

    filename_ext = os.path.basename(filepath) #gets file name with extension from path
    filename, ext = os.path.splitext(filename_ext) #separates file name and extension
    
    file = open(filepath, "rb")
    C = file.read()
    file.close()

    

    message = MyDecrypt(C, IV, key)
    
    writefile = open(filepath, "wb")
    writefile.write(message)
    writefile.close()

    return message, IV, key

def MyDecryptMAC(C, IV, tag, HMACKey, EncKey):
    
    h = hmac.HMAC(HMACKey, hashes.SHA256(), backend=default_backend())
    h.update(C)
    verifyTag = h.finalize()
    
    if verifyTag != tag:
        raise Exception("Tags do not align")
    
    message = MyDecrypt(C, IV, EncKey)
    
    return message

def MyFileDecryptMAC(originalfilepath, HMACKey):

    #getting file name and extension
    filename_ext = os.path.basename(originalfilepath) #gets file name with extension from path
    filename, ext = os.path.splitext(filename_ext) #separates file name and extension
    
    jsonFile = filename + ".json"
    
    #open file to decrypt
    with open(jsonFile) as decryptFile:
        data = json.load(decryptFile)
        decryptFile.close()

    #getting data from dictionary
    C = (data['C']).encode('cp437')
    IV = (data['IV']).encode('cp437')
    tag = (data['tag']).encode('cp437')
    EncKey = (data['EncKey']).encode('cp437')
    message = MyDecryptMAC(C, IV, tag, HMACKey, EncKey)
    
     #write recovered data to file
    recoveredFile = open(originalfilepath, "wb")
    recoveredFile.write(message)
    recoveredFile.close()
    
    #remove json file
    os.remove(jsonFile)
    
    return message


     #getting file name and extension
    filename_ext = os.path.basename(originalfilepath) #gets file name with extension from path
    filename, ext = os.path.splitext(filename_ext) #separates file name and extension
    
    jsonFile = filename + ".json"
    
    #open file to decrypt
    with open(jsonFile) as decryptFile:
        data = json.load(decryptFile)
        decryptFile.close()
    
    #getting data from dictionary
    C = (data['C']).encode('cp437')
    IV = (data['IV']).encode('cp437')
    tag = (data['tag']).encode('cp437')
    EncKey = (data['EncKey']).encode('cp437')
        
    message = MyDecryptMAC(C, IV, tag, HMACKey, EncKey)
    
    #write recovered data to file
    recoveredFile = open(originalfilepath, "wb")
    recoveredFile.write(message)
    recoveredFile.close()
    
    #remove json file
    os.remove(jsonFile)

    return message


#------------------------------------------------------------------------------

def main():
    #testFile = "test.txt"
    testFile = "test_photo.jpg"
    
    #C, IV, key, ext = MyFileEncrypt(testFile)
    #input("File encrypted! Press enter to decrypt.")
    
    #MyFileDecrypt(testFile, IV, key, ext)
    #print("\nFile decrypted!")
    
    C, IV, tag, EncKey, HMACKey, ext = MyFileEncryptMAC(testFile)
    input("File encrypted! Press enter to decrypt.")
    
    MyFileDecryptMAC(testFile, HMACKey)
    print("\nFile decrypted!")

main()

