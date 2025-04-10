from typing import Dict, Any

import hashlib
import json


class ProofOfWork:
    """Proof of Work implementation for anti-spam protection
    
    for the simplicity of the project, the PoW will only check if hash
    starts with a certain number of leading zeros. Idea is to
    overutilize the CPU of the client."""
    
    @staticmethod
    def get_target(difficulty: int) -> str:
        """get the target string (e.g., '0000' for difficulty 4)"""
        return '0' * difficulty
    
    @staticmethod
    def verify_proof(data: Dict[str, Any], difficulty: int) -> bool:
        if "nonce" not in data or "hash" not in data:
            return False
            
        verify_data = data.copy()
        del verify_data["hash"]
            
        data_string = json.dumps(verify_data, sort_keys=True)
        current_hash = hashlib.sha256(data_string.encode()).hexdigest()
        print(current_hash)
        
        target = ProofOfWork.get_target(difficulty)
        
        return current_hash == data["hash"] and current_hash.startswith(target)
