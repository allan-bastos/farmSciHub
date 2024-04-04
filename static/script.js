document.addEventListener('DOMContentLoaded', function () {
    const etapasLista = document.getElementById('etapas-lista');
    const salvarBtn = document.getElementById('salvar-btn');

    let draggedItem = null;

    etapasLista.addEventListener('dragstart', function (e) {
        draggedItem = e.target;
        e.dataTransfer.setData('text/plain', draggedItem.getAttribute('data-index'));
    });

    etapasLista.addEventListener('dragover', function (e) {
        e.preventDefault();
    });

    etapasLista.addEventListener('drop', function (e) {
        e.preventDefault();
        const dropIndex = e.target.getAttribute('data-index');
        const draggedIndex = e.dataTransfer.getData('text/plain');

        if (draggedIndex !== dropIndex) {
            const items = Array.from(etapasLista.children);
            const draggedItemIndex = items.findIndex(item => item.getAttribute('data-index') === draggedIndex);
            const dropItemIndex = items.findIndex(item => item.getAttribute('data-index') === dropIndex);

            etapasLista.insertBefore(items[draggedItemIndex], items[dropItemIndex]);
        }
    });

    etapasLista.addEventListener('dragend', function () {
        draggedItem = null;
    });

    salvarBtn.addEventListener('click', function () {
        const novaOrdem = Array.from(etapasLista.children).map((item, index) => {
            return { index: index, texto: item.innerText };
        });
    
        const experimentoId = extrairExperimentoIdDaUrl(); // Chamar a função para obter o ID do experimento
        enviarNovaOrdemAoBackend(novaOrdem, experimentoId);
    });
    

    function extrairExperimentoIdDaUrl() {
        const url = window.location.pathname;
        const partesDaUrl = url.split('/');
        const indexExperimentoId = partesDaUrl.indexOf('detalhes-experimento') + 1;
        return partesDaUrl[indexExperimentoId];
    }

    function enviarNovaOrdemAoBackend(novaOrdem, experimentoId) {
        // AJAX
        fetch(`/detalhes-experimento/${experimentoId}/etapas/atualizar_ordem`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ novaOrdem }),
        })
        .then(response => {
            if (response.ok) {
                window.location.href = `/detalhes-experimento/${experimentoId}/etapas`; // Redirecionamento após uma resposta bem-sucedida
            } else {
                throw new Error('Erro ao atualizar a ordem das etapas');
            }
        })
        .catch(error => console.error('Erro:', error));
    }
});
