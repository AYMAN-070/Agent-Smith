from sandbox.main_sandbox import Sandbox
from models import SandboxConfig
from agent.tools import create_task_specific_run_test


def run_agent_on_task(task_prompt: str, task_asserts: list[str]):
    """"
    La boucle principale de l'agent IA
    """
    print("--- Starting task ---")

    real_run_test = create_task_specific_run_test(task_asserts)

    injected_tools = {
        "agent_tools": {
            "run_test": real_run_test
        }
    }

    sandbox = Sandbox(config=SandboxConfig(), custom_modules=injected_tools)

    # --- BOUCLE DE L'IA ---
    # En réalité, ce code proviendra des réponses de l'API du LLM
    code_genere_par_ia = """
def sum_list(lst):
    return sum(lst)

from agent_tools import run_test
# L'IA teste son code sans même connaître les asserts secrets !
print(run_test(sum_list))

# Si l'IA lit "Success" dans le print, au tour suivant elle fera :
final_answer(sum_list([10, 20]))
"""

    # 4. Exécution dans votre moteur sécurisé
    resultat = sandbox.execute(code_genere_par_ia)

    # 5. L'Orchestrateur gère la réponse
    if resultat.get("status") == "final_answer":
        print(f"Mission accomplie. Réponse : {resultat.get('answer')}")
        return True
    elif resultat.get("status") == "success":
        print("L'IA a testé son code. Voici ce qu'elle a vu :")
        print(resultat.get("output"))
        # Le Dev A renverrait ce texte au LLM pour le tour suivant
    else:
        print(f"Le code de l'IA a planté : {resultat.get('error')}")
        # Le Dev A renverrait l'erreur au LLM
    return False
